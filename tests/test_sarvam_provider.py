"""Mocked contract tests for the Sarvam provider adapter."""

import io
import wave
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from sarvamai import ForbiddenError, TooManyRequestsError

from providers import sarvam


TEST_CONFIG = sarvam.SarvamConfig(api_key="secret-test-key")


def wav_bytes(seconds=1):
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\0\0" * 16000 * seconds)
    return buffer.getvalue()


def mock_client():
    return SimpleNamespace(
        speech_to_text=SimpleNamespace(transcribe=Mock()),
        chat=SimpleNamespace(completions=Mock()),
    )


def test_missing_environment_api_key(monkeypatch):
    monkeypatch.delenv("SARVAM_API_KEY", raising=False)
    with pytest.raises(sarvam.SarvamConfigurationError, match="SARVAM_API_KEY"):
        sarvam.SarvamConfig.from_env()


def test_empty_direct_api_key_is_rejected():
    for key in ("", " \t "):
        with pytest.raises(sarvam.SarvamConfigurationError, match="SARVAM_API_KEY"):
            sarvam.SarvamConfig(api_key=key)


def test_environment_configuration(monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", "configured-key")
    monkeypatch.setenv("SARVAM_STT_MODEL", "saaras:v4")
    monkeypatch.setenv("SARVAM_CHAT_MODEL", "sarvam-105b")
    monkeypatch.setenv("SARVAM_TIMEOUT_SECONDS", "12.5")
    config = sarvam.SarvamConfig.from_env()
    assert (config.stt_model, config.chat_model, config.timeout_seconds) == ("saaras:v4", "sarvam-105b", 12.5)


@pytest.mark.parametrize("timeout", [0, -1, "nan", 301])
def test_invalid_environment_timeout(monkeypatch, timeout):
    monkeypatch.setenv("SARVAM_API_KEY", "configured-key")
    monkeypatch.setenv("SARVAM_TIMEOUT_SECONDS", str(timeout))
    with pytest.raises(sarvam.SarvamConfigurationError):
        sarvam.SarvamConfig.from_env()


def test_invalid_direct_timeout():
    with pytest.raises(sarvam.SarvamConfigurationError):
        sarvam.SarvamConfig(api_key="key", timeout_seconds=0)


def test_empty_audio_is_rejected():
    with pytest.raises(sarvam.SarvamInputError, match="empty"):
        sarvam.transcribe_audio(b"", "clip.wav", "audio/wav", config=TEST_CONFIG, client=mock_client())


def test_invalid_audio_configuration_is_rejected():
    with pytest.raises(sarvam.SarvamInputError, match="content type"):
        sarvam.transcribe_audio(wav_bytes(), "clip.wav", "audio/mpeg", config=TEST_CONFIG, client=mock_client())
    with pytest.raises(sarvam.SarvamInputError, match="30 seconds"):
        sarvam.transcribe_audio(wav_bytes(31), "clip.wav", "audio/wav", config=TEST_CONFIG, client=mock_client())
    with pytest.raises(sarvam.SarvamInputError, match="valid"):
        sarvam.transcribe_audio(b"not wav", "clip.wav", "audio/wav", config=TEST_CONFIG, client=mock_client())


def test_detected_audio_format_must_match_filename_and_declared_mime(monkeypatch):
    monkeypatch.setattr(
        sarvam,
        "MutagenFile",
        lambda _file: SimpleNamespace(
            info=SimpleNamespace(length=1.0),
            mime=["audio/mpeg"],
        ),
    )
    with pytest.raises(sarvam.SarvamInputError, match="Detected audio format"):
        sarvam.transcribe_audio(
            wav_bytes(), "clip.wav", "audio/wav", config=TEST_CONFIG, client=mock_client()
        )


def test_maximum_audio_size_is_enforced():
    with pytest.raises(sarvam.SarvamInputError, match="25 MB"):
        sarvam.transcribe_audio(
            b"x" * (25 * 1024 * 1024 + 1), "clip.wav", "audio/wav", config=TEST_CONFIG, client=mock_client()
        )


def test_successful_transcription_returns_editable_normalized_fields():
    client = mock_client()
    client.speech_to_text.transcribe.return_value = SimpleNamespace(
        transcript="  नमस्ते  ", language_code="hi-IN", language_probability=0.98, request_id="req-1"
    )
    result = sarvam.transcribe_audio(
        wav_bytes(), "clip.wav", "audio/wav", language_code="hi-IN", config=TEST_CONFIG, client=client
    )
    assert result == {
        "transcript": "नमस्ते", "language_code": "hi-IN", "language_probability": 0.98,
        "request_id": "req-1", "model": "saaras:v4"
    }
    assert client.speech_to_text.transcribe.call_args.kwargs["model"] == "saaras:v4"


def test_provider_timeout_is_safe():
    client = mock_client()
    client.chat.completions.side_effect = httpx.ReadTimeout("secret-test-key private prompt")
    with pytest.raises(sarvam.SarvamTimeoutError) as error:
        sarvam.generate_response([{"role": "user", "content": "hello"}], config=TEST_CONFIG, client=client)
    assert "secret-test-key" not in str(error.value)
    assert "private prompt" not in str(error.value)


@pytest.mark.parametrize(
    "error_type, expected",
    [(ForbiddenError, sarvam.SarvamAuthenticationError), (TooManyRequestsError, sarvam.SarvamRateLimitError)],
)
def test_sdk_authentication_and_rate_limit_failures(error_type, expected):
    error = error_type({"message": "secret-test-key provider body"})
    client = mock_client()
    client.speech_to_text.transcribe.side_effect = error
    with pytest.raises(expected) as caught:
        sarvam.transcribe_audio(wav_bytes(), "clip.wav", "audio/wav", config=TEST_CONFIG, client=client)
    assert "secret-test-key" not in str(caught.value)


def test_successful_chat_response():
    client = mock_client()
    client.chat.completions.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="  Review road access.  "))],
        model="sarvam-105b",
    )
    result = sarvam.generate_response(
        [{"role": "user", "content": "What should the analyst inspect?"}], config=TEST_CONFIG, client=client
    )
    assert result == {"text": "Review road access.", "model": "sarvam-105b"}
    assert client.chat.completions.call_args.kwargs["max_tokens"] == 800


def test_invalid_message_structure_and_unsupported_role():
    with pytest.raises(sarvam.SarvamInputError):
        sarvam.generate_response([{"role": "tool", "content": "bad"}], config=TEST_CONFIG, client=mock_client())
    with pytest.raises(sarvam.SarvamInputError, match="role"):
        sarvam.generate_response([{"role": "function", "content": "bad"}], config=TEST_CONFIG, client=mock_client())


def test_tool_message_requires_and_accepts_tool_call_id():
    client = mock_client()
    client.chat.completions.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="done"))], model="sarvam-105b"
    )
    messages = [
        {"role": "user", "content": "lookup"},
        {"role": "tool", "content": "lookup result", "tool_call_id": "call_123"},
    ]
    sarvam.generate_response(messages, config=TEST_CONFIG, client=client)
    assert client.chat.completions.call_args.kwargs["messages"][1]["tool_call_id"] == "call_123"


def test_system_instructions_must_precede_conversation_content():
    with pytest.raises(sarvam.SarvamInputError, match="precede"):
        sarvam.generate_response(
            [{"role": "user", "content": "note"}, {"role": "system", "content": "instructions"}],
            config=TEST_CONFIG,
            client=mock_client(),
        )


@pytest.mark.parametrize("token_limit", [1, 4096])
def test_max_output_token_boundaries(token_limit):
    client = mock_client()
    client.chat.completions.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))], model="sarvam-105b"
    )
    sarvam.generate_response(
        [{"role": "user", "content": "hello"}], max_tokens=token_limit, config=TEST_CONFIG, client=client
    )
    assert client.chat.completions.call_args.kwargs["max_tokens"] == token_limit


def test_unsupported_chat_model_is_rejected():
    with pytest.raises(sarvam.SarvamInputError, match="model"):
        sarvam.generate_response(
            [{"role": "user", "content": "hello"}], model="glm5.3", config=TEST_CONFIG, client=mock_client()
        )


@pytest.mark.parametrize("model", ["sarvam-105b", "sarvam-105b-conversations"])
def test_v1_supported_chat_models(model):
    client = mock_client()
    client.chat.completions.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))], model=model
    )
    sarvam.generate_response(
        [{"role": "user", "content": "hello"}], model=model, config=TEST_CONFIG, client=client
    )
    assert client.chat.completions.called
    assert client.chat.completions.call_args.kwargs["model"] == model


@pytest.mark.parametrize("token_limit", [0, 4097])
def test_output_token_limits_reject_out_of_range(token_limit):
    with pytest.raises(sarvam.SarvamInputError, match="max_tokens"):
        sarvam.generate_response(
            [{"role": "user", "content": "hello"}], max_tokens=token_limit,
            config=TEST_CONFIG, client=mock_client()
        )


def test_oversized_chat_context():
    with pytest.raises(sarvam.SarvamInputError, match="80,000"):
        sarvam.generate_response(
            [{"role": "user", "content": "x" * 16_000} for _ in range(6)],
            config=TEST_CONFIG,
            client=mock_client(),
        )


def test_secret_never_appears_in_user_facing_errors():
    client = mock_client()
    client.chat.completions.side_effect = RuntimeError("secret-test-key /private provider response")
    with pytest.raises(sarvam.SarvamRequestError) as caught:
        sarvam.generate_response([{"role": "user", "content": "private prompt"}], config=TEST_CONFIG, client=client)
    assert "secret-test-key" not in str(caught.value)
    assert "private" not in str(caught.value)


@pytest.mark.parametrize("response", [SimpleNamespace(choices=[]), SimpleNamespace(choices=None)])
def test_malformed_chat_response_is_safe(response):
    client = mock_client()
    client.chat.completions.return_value = response
    with pytest.raises(sarvam.SarvamRequestError, match="invalid chat response"):
        sarvam.generate_response([{"role": "user", "content": "hello"}], config=TEST_CONFIG, client=client)


def test_malformed_transcription_response_is_safe():
    client = mock_client()
    client.speech_to_text.transcribe.return_value = SimpleNamespace(transcript=None)
    with pytest.raises(sarvam.SarvamRequestError, match="invalid transcription response"):
        sarvam.transcribe_audio(wav_bytes(), "clip.wav", "audio/wav", config=TEST_CONFIG, client=client)
