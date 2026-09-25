from __future__ import annotations

from functools import lru_cache

from app.core.config import Settings


@lru_cache
def _get_model(model_size: str):
    from faster_whisper import WhisperModel

    return WhisperModel(model_size, device="cpu", compute_type="int8")


def transcribe_audio(settings: Settings, audio_path: str) -> tuple[str, str]:
    model = _get_model(settings.whisper_model_size)
    segments, info = model.transcribe(audio_path, beam_size=1)
    text = " ".join(segment.text.strip() for segment in segments).strip()
    return text, info.language
