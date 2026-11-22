"""Pre-parser body limits for Sarvam endpoints."""

from __future__ import annotations

import asyncio
import json
import math
import threading
import tempfile
import time

import anyio


SARVAM_AUDIO_MAX_BYTES = 25 * 1024 * 1024
MULTIPART_OVERHEAD_BYTES = 64 * 1024
SARVAM_TRANSCRIBE_BODY_MAX = SARVAM_AUDIO_MAX_BYTES + MULTIPART_OVERHEAD_BYTES
SARVAM_CHAT_BODY_MAX = 128 * 1024
_BODY_MEMORY_SPOOL_BYTES = 1024 * 1024
_BODY_READ_CHUNK_BYTES = 64 * 1024
_MAX_BUFFERED_SARVAM_REQUESTS = threading.BoundedSemaphore(2)
DEFAULT_UPLOAD_IDLE_TIMEOUT_SECONDS = 10.0
DEFAULT_UPLOAD_MAX_DURATION_SECONDS = 120.0
MAX_UPLOAD_IDLE_TIMEOUT_SECONDS = 60.0
MAX_UPLOAD_DURATION_SECONDS = 600.0


class SarvamRequestBodyLimitMiddleware:
    """Cap Sarvam bodies before FastAPI or Starlette parses them.

    Bodies are streamed to a small in-memory spool that rolls over to a temporary
    file. The body is replayed in bounded chunks to the downstream ASGI app.
    """

    _limits = {
        ("POST", "/api/v1/sarvam/transcribe"): SARVAM_TRANSCRIBE_BODY_MAX,
        ("POST", "/api/v1/sarvam/chat"): SARVAM_CHAT_BODY_MAX,
    }

    def __init__(
        self,
        app,
        *,
        idle_timeout_seconds: float = DEFAULT_UPLOAD_IDLE_TIMEOUT_SECONDS,
        max_duration_seconds: float = DEFAULT_UPLOAD_MAX_DURATION_SECONDS,
        max_buffered_requests: int = 2,
    ):
        if (
            not math.isfinite(idle_timeout_seconds)
            or not 0 < idle_timeout_seconds <= MAX_UPLOAD_IDLE_TIMEOUT_SECONDS
        ):
            raise ValueError("Upload idle timeout must be positive and at most 60 seconds.")
        if (
            not math.isfinite(max_duration_seconds)
            or not 0 < max_duration_seconds <= MAX_UPLOAD_DURATION_SECONDS
        ):
            raise ValueError("Maximum upload duration must be positive and at most 600 seconds.")
        if max_buffered_requests < 1:
            raise ValueError("At least one buffered request slot is required.")
        self.app = app
        self.idle_timeout_seconds = idle_timeout_seconds
        self.max_duration_seconds = max_duration_seconds
        self._request_slots = (
            _MAX_BUFFERED_SARVAM_REQUESTS
            if max_buffered_requests == 2
            else threading.BoundedSemaphore(max_buffered_requests)
        )

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        limit = self._limits.get((scope.get("method", ""), scope.get("path", "")))
        if limit is None:
            await self.app(scope, receive, send)
            return

        lengths = [value for key, value in scope.get("headers", []) if key.lower() == b"content-length"]
        if len(lengths) > 1:
            await self._reject(send, 400, "Invalid Content-Length header.")
            return
        if lengths:
            try:
                raw_length = lengths[0].decode("ascii")
                if not raw_length.isdecimal():
                    raise ValueError
                declared_length = int(raw_length)
            except (UnicodeDecodeError, ValueError):
                await self._reject(send, 400, "Invalid Content-Length header.")
                return
            if declared_length > limit:
                await self._reject(send, 413, "Request body exceeds the upload limit.")
                return

        if not self._request_slots.acquire(blocking=False):
            await self._reject(send, 429, "Upload capacity is temporarily full.")
            return

        total = 0
        spool = None
        try:
            started_at = time.monotonic()
            spool = tempfile.SpooledTemporaryFile(max_size=_BODY_MEMORY_SPOOL_BYTES, mode="w+b")
            while True:
                remaining_duration = self.max_duration_seconds - (time.monotonic() - started_at)
                if remaining_duration <= 0:
                    await self._reject(send, 408, "Request body upload timed out.")
                    return
                try:
                    message = await asyncio.wait_for(
                        receive(),
                        timeout=min(self.idle_timeout_seconds, remaining_duration),
                    )
                except asyncio.TimeoutError:
                    await self._reject(send, 408, "Request body upload timed out.")
                    return
                if message["type"] == "http.disconnect":
                    return
                if message["type"] != "http.request":
                    await self._reject(send, 400, "Malformed request body stream.")
                    return
                chunk = message.get("body", b"")
                total += len(chunk)
                if total > limit:
                    await self._reject(send, 413, "Request body exceeds the upload limit.")
                    return
                if chunk:
                    await anyio.to_thread.run_sync(spool.write, chunk)
                if time.monotonic() - started_at >= self.max_duration_seconds:
                    await self._reject(send, 408, "Request body upload timed out.")
                    return
                if not message.get("more_body", False):
                    break

            await anyio.to_thread.run_sync(spool.seek, 0)
            remaining = total
            final_message_sent = False

            async def replay_body():
                nonlocal remaining, final_message_sent
                if remaining <= 0:
                    if not final_message_sent:
                        final_message_sent = True
                        return {"type": "http.request", "body": b"", "more_body": False}
                    return {"type": "http.disconnect"}
                chunk = await anyio.to_thread.run_sync(
                    spool.read, min(_BODY_READ_CHUNK_BYTES, remaining)
                )
                remaining -= len(chunk)
                more_body = remaining > 0
                if not more_body:
                    final_message_sent = True
                return {"type": "http.request", "body": chunk, "more_body": more_body}

            await self.app(scope, replay_body, send)
        finally:
            try:
                if spool is not None:
                    spool.close()
            finally:
                self._request_slots.release()

    @staticmethod
    async def _reject(send, status_code: int, detail: str) -> None:
        body = json.dumps({"detail": detail}).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": status_code,
                "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
            }
        )
        await send({"type": "http.response.body", "body": body, "more_body": False})
