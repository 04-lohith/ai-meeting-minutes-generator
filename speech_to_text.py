"""
speech_to_text.py — Whisper transcription module.

Loads the OpenAI Whisper model and converts meeting audio files
into text transcripts.
"""

import whisper

# Module-level cache so the model is loaded only once per session.
_model_cache: dict[str, whisper.Whisper] = {}


def _get_model(model_size: str = "medium") -> whisper.Whisper:
    """Load (and cache) a Whisper model."""
    if model_size not in _model_cache:
        _model_cache[model_size] = whisper.load_model(model_size)
    return _model_cache[model_size]


def transcribe_audio(file_path: str, model_size: str = "medium") -> str:
    """Transcribe an audio file using OpenAI Whisper.

    Args:
        file_path: Path to the audio file (WAV, MP3, etc.).
        model_size: Whisper model variant — "medium" recommended for
                    meeting-quality transcription. Larger models are more
                    accurate but slower.

    Returns:
        The full transcript as a single string.
    """
    model = _get_model(model_size)
    result = model.transcribe(
        file_path,
        fp16=False,  # safer on CPU / MPS
        language="en",
    )
    return result["text"].strip()
