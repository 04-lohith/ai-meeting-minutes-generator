"""
llm_processor.py — LLM processing module.

Supports two backends:
  1. Ollama (local, default) — no API key needed
  2. Google Gemini (cloud) — requires GOOGLE_API_KEY

Sends the meeting transcript to the LLM and asks for structured
meeting minutes (summary, action_items, decisions) in JSON format.
"""

import json
import os
import re
import time
import requests

from dotenv import load_dotenv

load_dotenv()

# ── Prompt Template ─────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are an expert AI meeting assistant.

Convert the following meeting transcript into structured meeting minutes.

Return **only** valid JSON with exactly this structure — no markdown fences,
no commentary, just the raw JSON object:

{
  "summary": "A concise paragraph summarising the key discussion points.",
  "action_items": [
    {
      "person": "Name of the responsible person",
      "task": "Description of the action item",
      "deadline": "Stated or inferred deadline, or 'Not specified'"
    }
  ],
  "decisions": [
    "Each major decision made during the meeting"
  ]
}

Rules:
1. Extract ALL action items mentioned, even implicit ones.
2. If a speaker states their name before speaking (e.g. "Rahul: ..."),
   use that name for attribution.
3. If no deadline is mentioned, write "Not specified".
4. Keep the summary to 2-3 sentences.
5. Return ONLY the JSON object — nothing else.
"""


# ── Ollama (Local LLM) ─────────────────────────────────────────

OLLAMA_URL = "http://127.0.0.1:11434"


def _ollama_available() -> bool:
    """Check if the Ollama server is running."""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def _ollama_models() -> list[str]:
    """List models available in Ollama."""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        data = r.json()
        return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def _generate_with_ollama(transcript: str, model: str = "llama3.2") -> dict:
    """Generate meeting minutes using a local Ollama model."""
    prompt = f"{SYSTEM_PROMPT}\n\nTranscript:\n{transcript}"

    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3},
        },
        timeout=300,  # local models can be slow
    )
    response.raise_for_status()
    result = response.json()
    return _parse_response(result["response"])


# ── Gemini (Cloud LLM) ─────────────────────────────────────────

def _generate_with_gemini(transcript: str, api_key: str) -> dict:
    """Generate meeting minutes using Google Gemini."""
    import google.generativeai as genai

    genai.configure(api_key=api_key)

    models = ["gemini-2.0-flash-lite", "gemini-1.5-flash", "gemini-2.0-flash"]
    last_error = None

    for model_name in models:
        for attempt in range(2):
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(
                    f"{SYSTEM_PROMPT}\n\nTranscript:\n{transcript}"
                )
                return _parse_response(response.text)
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                if "429" in error_str or "quota" in error_str or "rate" in error_str:
                    if attempt < 1:
                        time.sleep(30)
                        continue
                    else:
                        break
                elif "404" in error_str:
                    break
                else:
                    raise

    raise RuntimeError(
        f"All Gemini models hit rate limits. Wait a minute and retry.\n"
        f"Last error: {last_error}"
    )


# ── Public API ──────────────────────────────────────────────────

def generate_minutes(transcript: str, api_key: str | None = None,
                     provider: str = "ollama", ollama_model: str = "llama3.2") -> dict:
    """Generate structured meeting minutes from a transcript.

    Args:
        transcript: The full meeting transcript.
        api_key: Gemini API key (only needed if provider="gemini").
        provider: "ollama" for local LLM, "gemini" for cloud.
        ollama_model: Which Ollama model to use.

    Returns:
        A dict with keys: summary, action_items, decisions.
    """
    if provider == "ollama":
        if not _ollama_available():
            raise RuntimeError(
                "Ollama server is not running. Start it with: ollama serve\n"
                "Then pull a model: ollama pull llama3.2"
            )
        return _generate_with_ollama(transcript, model=ollama_model)

    else:  # gemini
        key = api_key or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise ValueError(
                "Google API key is required for Gemini. "
                "Set GOOGLE_API_KEY or enter it in the sidebar."
            )
        return _generate_with_gemini(transcript, api_key=key)


# ── Helpers ─────────────────────────────────────────────────────

def _parse_response(text: str) -> dict:
    """Extract and validate JSON from the LLM response."""
    cleaned = re.sub(r"```(?:json)?\s*", "", text).strip()
    cleaned = cleaned.rstrip("`").strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Failed to parse LLM response as JSON.\n"
            f"Raw response:\n{text}"
        ) from exc

    for key in ("summary", "action_items", "decisions"):
        if key not in data:
            raise RuntimeError(
                f"LLM response is missing required key '{key}'.\n"
                f"Parsed data: {data}"
            )

    return data
