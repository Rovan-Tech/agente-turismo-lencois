from unittest.mock import MagicMock

from app.core.config import get_settings
from app.services import transcription


class _FakeSegment:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeInfo:
    def __init__(self, language: str) -> None:
        self.language = language


def test_transcribe_audio_joins_segments_and_strips_whitespace(monkeypatch):
    fake_model = MagicMock()
    fake_model.transcribe.return_value = (
        [_FakeSegment("  olá "), _FakeSegment("tudo bem? ")],
        _FakeInfo("pt"),
    )
    monkeypatch.setattr(transcription, "_get_model", lambda model_size: fake_model)

    text, language = transcription.transcribe_audio(get_settings(), "audio-path.ogg")

    assert text == "olá tudo bem?"
    assert language == "pt"
    fake_model.transcribe.assert_called_once_with("audio-path.ogg", beam_size=1)


def test_transcribe_audio_uses_configured_model_size(monkeypatch):
    captured = {}

    def fake_get_model(model_size):
        captured["model_size"] = model_size
        fake_model = MagicMock()
        fake_model.transcribe.return_value = ([], _FakeInfo("en"))
        return fake_model

    monkeypatch.setattr(transcription, "_get_model", fake_get_model)
    settings = get_settings()
    monkeypatch.setattr(settings, "whisper_model_size", "small")

    text, language = transcription.transcribe_audio(settings, "audio-path.ogg")

    assert captured["model_size"] == "small"
    assert text == ""
    assert language == "en"
