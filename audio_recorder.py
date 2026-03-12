"""
audio_recorder.py — Audio handling module.

Saves audio captured via Streamlit's st.audio_input() widget to a WAV file
in the outputs/ directory for Whisper transcription.
"""

import os
import datetime


def save_audio_bytes(audio_bytes: bytes, output_dir: str = "outputs") -> str:
    """Save raw audio bytes (from st.audio_input) to a WAV file.

    Args:
        audio_bytes: Raw audio bytes from the Streamlit audio widget.
        output_dir: Directory to save the file in.

    Returns:
        Absolute path to the saved audio file.
    """
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"meeting_{timestamp}.wav"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "wb") as f:
        f.write(audio_bytes)

    return os.path.abspath(filepath)
