"""Pre-parser body limits for Sarvam endpoints."""

from __future__ import annotations

import json
import threading
import tempfile

import anyio


SARVAM_AUDIO_MAX_BYTES = 25 * 1024 * 1024
MULTIPART_OVERHEAD_BYTES = 64 * 1024
SARVAM_TRANSCRIBE_BODY_MAX = SARVAM_AUDIO_MAX_BYTES + MULTIPART_OVERHEAD_BYTES
SARVAM_CHAT_BODY_MAX = 128 * 1024
_BODY_MEMORY_SPOOL_BYTES = 1024 * 1024
_BODY_READ_CHUNK_BYTES = 64 * 1024
_MAX_BUFFERED_SARVAM_REQUESTS = threading.BoundedSemaphore(2)


class SarvamRequestBodyLimitMiddleware:
    """Cap Sarvam bodies before FastAPI or Starlette parses them.

    Bodies are streamed to a small in-memory spool that rolls over to a temporary
    file. The body is replayed in bounded chunks to the downstream ASGI app.
    """

    _limits = {
        ("POST", "/api/v1/sarvam/transcribe"): SARVAM_TRANSCRIBE_BODY_MAX,
        ("POST", "/api/v1/sarvam/chat"): SARVAM_CHAT_BODY_MAX,
    }

    def __init__(self, app):
        self.app = app

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

        if not _MAX_BUFFERED_SARVAM_REQUESTS.acquire(blocking=False):
            await self._reject(send, 429, "Upload capacity is temporarily full.")
            return

        total = 0
        spool = tempfile.SpooledTemporaryFile(max_size=_BODY_MEMORY_SPOOL_BYTES, mode="w+b")
        try:
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                if message["type"] != "http.request":
                    continue
                chunk = message.get("body", b"")
                total += len(chunk)
                if total > limit:
                    await self._reject(send, 413, "Request body exceeds the upload limit.")
                    return
                if chunk:
                    await anyio.to_thread.run_sync(spool.write, chunk)
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
            spool.close()
            _MAX_BUFFERED_SARVAM_REQUESTS.release()

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
