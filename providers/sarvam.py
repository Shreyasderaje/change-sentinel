"""Small, FastAPI-independent adapter for Sarvam speech and chat APIs."""

from __future__ import annotations

import io
import os
import wave
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import httpx
from mutagen import File as MutagenFile
from sarvamai import ForbiddenError, TooManyRequestsError
from sarvamai.core.api_error import ApiError


class SarvamProviderError(RuntimeError):
    """Safe base error suitable for translation into an API response."""


class SarvamConfigurationError(SarvamProviderError):
    pass


class SarvamInputError(SarvamProviderError):
    pass


class SarvamAuthenticationError(SarvamProviderError):
    pass


class SarvamRateLimitError(SarvamProviderError):
    pass


class SarvamTimeoutError(SarvamProviderError):
    pass


class SarvamRequestError(SarvamProviderError):
    pass


@dataclass(frozen=True)
class SarvamConfig:
    api_key: str
    stt_model: str = "saaras:v4"
    chat_model: str = "sarvam-105b"
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        if not isinstance(self.api_key, str) or not self.api_key.strip():
            raise SarvamConfigurationError("A non-empty SARVAM_API_KEY is required.")
        object.__setattr__(self, "api_key", self.api_key.strip())
        if isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, (int, float)):
            raise SarvamConfigurationError("SARVAM_TIMEOUT_SECONDS must be a positive number.")
        if not 0 < float(self.timeout_seconds) <= 300:
            raise SarvamConfigurationError("SARVAM_TIMEOUT_SECONDS must be greater than 0 and at most 300.")

    @classmethod
    def from_env(cls) -> "SarvamConfig":
        key = os.getenv("SARVAM_API_KEY", "").strip()
        if not key:
            raise SarvamConfigurationError("SARVAM_API_KEY is required to use Sarvam services.")
        try:
            timeout = float(os.getenv("SARVAM_TIMEOUT_SECONDS", "30"))
        except ValueError:
            raise SarvamConfigurationError("SARVAM_TIMEOUT_SECONDS must be a positive number.") from None
        if not 0 < timeout <= 300:
            raise SarvamConfigurationError("SARVAM_TIMEOUT_SECONDS must be greater than 0 and at most 300.")
        return cls(
            api_key=key,
            stt_model=os.getenv("SARVAM_STT_MODEL", "saaras:v4").strip() or "saaras:v4",
            chat_model=os.getenv("SARVAM_CHAT_MODEL", "sarvam-105b").strip() or "sarvam-105b",
            timeout_seconds=timeout,
        )


_AUDIO_TYPES = {
    ".wav": {"audio/wav", "audio/x-wav", "audio/wave", "application/octet-stream"},
    ".mp3": {"audio/mpeg", "audio/mp3", "application/octet-stream"},
    ".aac": {"audio/aac", "application/octet-stream"},
    ".aiff": {"audio/aiff", "audio/x-aiff", "application/octet-stream"},
    ".aif": {"audio/aiff", "audio/x-aiff", "application/octet-stream"},
    ".ogg": {"audio/ogg", "application/ogg", "application/octet-stream"},
    ".opus": {"audio/opus", "audio/ogg", "application/octet-stream"},
    ".flac": {"audio/flac", "audio/x-flac", "application/octet-stream"},
    ".m4a": {"audio/mp4", "audio/x-m4a", "application/octet-stream"},
    ".mp4": {"audio/mp4", "video/mp4", "application/octet-stream"},
    ".amr": {"audio/amr", "application/octet-stream"},
    ".wma": {"audio/x-ms-wma", "audio/wma", "application/octet-stream"},
    ".webm": {"audio/webm", "application/octet-stream"},
    ".pcm": {"audio/pcm", "application/octet-stream"},
}
_TRANSCRIPTION_MODES = {"transcribe", "translate", "verbatim", "translit", "codemix"}
_ALLOWED_LANGUAGES = {
    "unknown", "hi-IN", "bn-IN", "kn-IN", "ml-IN", "mr-IN", "od-IN", "pa-IN",
    "ta-IN", "te-IN", "en-IN", "gu-IN", "as-IN", "ur-IN", "ne-IN", "kok-IN",
    "ks-IN", "sd-IN", "sa-IN", "sat-IN", "mni-IN", "brx-IN", "mai-IN", "doi-IN",
}
_MAX_AUDIO_BYTES = 25 * 1024 * 1024
_MAX_MESSAGES = 50
_MAX_MESSAGE_CHARS = 20_000
_MAX_CONTEXT_CHARS = 80_000
_DEFAULT_MAX_TOKENS = 800
_MAX_OUTPUT_TOKENS = 4_096


def _client(config: SarvamConfig, client: Any | None) -> Any:
    if client is not None:
        return client
    try:
        from sarvamai import SarvamAI
    except ImportError:
        raise SarvamConfigurationError("The sarvamai SDK is not installed.") from None
    try:
        return SarvamAI(api_subscription_key=config.api_key, timeout=config.timeout_seconds)
    except Exception:
        raise SarvamConfigurationError("Could not initialize the Sarvam client.") from None


def _translate_sdk_error(exc: Exception) -> SarvamProviderError:
    """Convert SDK/transport errors to safe messages without echoing error bodies."""
    if isinstance(exc, httpx.TimeoutException):
        return SarvamTimeoutError("Sarvam request timed out.")
    if ForbiddenError and isinstance(exc, ForbiddenError):
        return SarvamAuthenticationError("Sarvam rejected the configured credentials.")
    if TooManyRequestsError and isinstance(exc, TooManyRequestsError):
        return SarvamRateLimitError("Sarvam rate limit reached. Please retry later.")
    if ApiError and isinstance(exc, ApiError):
        status = getattr(exc, "status_code", None)
        if status == 403:
            return SarvamAuthenticationError("Sarvam rejected the configured credentials.")
        if status == 429:
            return SarvamRateLimitError("Sarvam rate limit reached. Please retry later.")
        return SarvamRequestError("Sarvam could not process the request.")
    return SarvamRequestError("Sarvam request failed.")


def _validate_audio(audio_bytes: bytes, filename: str, content_type: str) -> tuple[str, float | None]:
    if not isinstance(audio_bytes, (bytes, bytearray)) or not audio_bytes:
        raise SarvamInputError("Audio file is empty.")
    if len(audio_bytes) > _MAX_AUDIO_BYTES:
        raise SarvamInputError("Audio file exceeds the 25 MB upload limit.")
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in _AUDIO_TYPES:
        raise SarvamInputError("Unsupported audio format.")
    mime = (content_type or "application/octet-stream").split(";", 1)[0].strip().lower()
    if mime not in _AUDIO_TYPES[ext]:
        raise SarvamInputError("Audio content type does not match the file format.")

    duration: float | None = None
    if ext == ".pcm":
        # PCM REST input must be 16 kHz. Without a specified codec/channel count,
        # duration cannot safely be inferred from a filename or MIME type.
        raise SarvamInputError("Raw PCM audio is not supported without explicit codec metadata.")
    try:
        media = MutagenFile(io.BytesIO(bytes(audio_bytes)))
        duration = float(media.info.length) if media and media.info and media.info.length else None
    except Exception:
        duration = None
    if duration is None and ext == ".wav":
        try:
            with wave.open(io.BytesIO(bytes(audio_bytes)), "rb") as wav_file:
                duration = wav_file.getnframes() / float(wav_file.getframerate())
        except (wave.Error, EOFError, ZeroDivisionError):
            duration = None
    if duration is None:
        raise SarvamInputError("Audio file is invalid or its duration could not be verified.")
    if duration <= 0 or duration > 30:
        raise SarvamInputError("Audio must be longer than 0 seconds and no longer than 30 seconds.")
    return ext, duration


def transcribe_audio(
    audio_bytes: bytes,
    filename: str,
    content_type: str,
    mode: str = "transcribe",
    language_code: str | None = None,
    *,
    client: Any | None = None,
    config: SarvamConfig | None = None,
) -> dict[str, Any]:
    """Transcribe a verified short audio clip; transcript remains editable by caller."""
    config = config or SarvamConfig.from_env()
    _ext, _duration = _validate_audio(audio_bytes, filename, content_type)
    if mode not in _TRANSCRIPTION_MODES:
        raise SarvamInputError("Unsupported transcription mode.")
    if language_code is not None and language_code not in _ALLOWED_LANGUAGES:
        raise SarvamInputError("Unsupported language_code.")
    service = _client(config, client)
    file_obj = io.BytesIO(bytes(audio_bytes))
    file_obj.name = os.path.basename(filename)
    kwargs: dict[str, Any] = {
        "file": (os.path.basename(filename), file_obj, content_type),
        "model": config.stt_model,
        "mode": mode,
    }
    if language_code:
        kwargs["language_code"] = language_code
    try:
        response = service.speech_to_text.transcribe(**kwargs)
    except Exception as exc:
        raise _translate_sdk_error(exc) from None
    transcript = getattr(response, "transcript", None)
    if not isinstance(transcript, str):
        raise SarvamRequestError("Sarvam returned an invalid transcription response.")
    return {
        "transcript": transcript.strip(),
        "language_code": getattr(response, "language_code", None),
        "language_probability": getattr(response, "language_probability", None),
        "request_id": getattr(response, "request_id", None),
        "model": config.stt_model,
    }


def _validate_messages(messages: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    if not isinstance(messages, (list, tuple)) or not messages or len(messages) > _MAX_MESSAGES:
        raise SarvamInputError("messages must contain between 1 and 50 entries.")
    normalized: list[dict[str, str]] = []
    total_chars = 0
    user_content_seen = False
    for message in messages:
        if not isinstance(message, Mapping) or "role" not in message:
            raise SarvamInputError("Each message must contain a role and its required fields.")
        role = message["role"]
        if role not in {"system", "developer", "user", "assistant", "tool"}:
            raise SarvamInputError("Message role is not supported.")
        if role in {"system", "developer"} and user_content_seen:
            raise SarvamInputError("System and developer instructions must precede conversation content.")
        if role == "tool":
            if set(message) != {"role", "content", "tool_call_id"}:
                raise SarvamInputError("Tool messages require content and tool_call_id only.")
            tool_call_id = message["tool_call_id"]
            if not isinstance(tool_call_id, str) or not tool_call_id.strip() or len(tool_call_id) > 256:
                raise SarvamInputError("Tool message tool_call_id must be non-empty text of at most 256 characters.")
        elif set(message) != {"role", "content"}:
            raise SarvamInputError("Messages require only role and content.")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip() or len(content) > _MAX_MESSAGE_CHARS:
            raise SarvamInputError("Message content must be non-empty text of at most 20,000 characters.")
        total_chars += len(content)
        if role in {"user", "assistant"}:
            user_content_seen = True
        normalized_message = {"role": role, "content": content}
        if role == "tool":
            normalized_message["tool_call_id"] = tool_call_id
        normalized.append(normalized_message)
    if total_chars > _MAX_CONTEXT_CHARS:
        raise SarvamInputError("Chat context exceeds the 80,000 character limit.")
    return normalized


def generate_response(
    messages: Sequence[Mapping[str, Any]],
    model: str | None = None,
    max_tokens: int = _DEFAULT_MAX_TOKENS,
    *,
    client: Any | None = None,
    config: SarvamConfig | None = None,
) -> dict[str, str]:
    """Generate a chat completion from caller-provided context only."""
    config = config or SarvamConfig.from_env()
    normalized_messages = _validate_messages(messages)
    selected_model = config.chat_model if model is None else model
    if selected_model not in {"sarvam-105b", "sarvam-105b-conversations"}:
        raise SarvamInputError("Unsupported Sarvam chat model.")
    if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or not 1 <= max_tokens <= _MAX_OUTPUT_TOKENS:
        raise SarvamInputError("max_tokens must be an integer from 1 to 4096.")
    service = _client(config, client)
    try:
        response = service.chat.completions(
            model=selected_model,
            messages=normalized_messages,
            max_tokens=max_tokens,
            request_options={"timeout_in_seconds": config.timeout_seconds},
        )
    except Exception as exc:
        raise _translate_sdk_error(exc) from None
    try:
        text = response.choices[0].message.content
    except (AttributeError, IndexError, TypeError):
        raise SarvamRequestError("Sarvam returned an invalid chat response.") from None
    if not isinstance(text, str):
        raise SarvamRequestError("Sarvam returned an invalid chat response.")
    return {"text": text.strip(), "model": getattr(response, "model", selected_model)}
