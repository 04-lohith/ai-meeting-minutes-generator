# MinuteMaster AI — Meeting Minutes Generator

Record meetings, transcribe with Whisper, generate structured minutes with a local LLM (Ollama). Runs **100% locally** — no cloud APIs required.

---

## Quick Start

### 1. Clone

```bash
git clone https://github.com/<your-username>/AI_MOM_Generater.git
cd AI_MOM_Generater
```

### 2. Install Ollama (Local LLM)

```bash
# macOS / Linux
curl -fsSL https://ollama.com/install.sh | sh

# Start the server (keep this terminal open)
ollama serve

# Pull a model (in a new terminal)
ollama pull llama3.2
```

### 3. Set up Python environment

```bash
conda create -n meeting-ai python=3.11 ffmpeg portaudio -c conda-forge -y
conda activate meeting-ai

# Install Whisper separately (needs special build flags)
pip install setuptools wheel
pip install openai-whisper --no-build-isolation

# Install remaining dependencies
pip install -r requirements.txt
```

### 4. Pre-download Whisper model

```bash
python -c "import whisper; whisper.load_model('base'); print('Ready!')"
```

### 5. Run

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Streamlit UI (app.py)                    │
│  ┌──────────┐    ┌──────────────┐    ┌────────────────────────┐ │
│  │ Audio    │───▶│ Transcription│───▶│ LLM Processing         │ │
│  │ Capture  │    │              │    │                        │ │
│  │          │    │  Whisper     │    │  Ollama / Gemini       │ │
│  └──────────┘    └──────────────┘    └───────────┬────────────┘ │
│       ▲                                          │              │
│  Browser Mic                                     ▼              │
│  File Upload                            ┌────────────────┐     │
│  Paste Text                             │ Structured JSON │     │
│                                         │ (summary,       │     │
│                                         │  action_items,  │     │
│                                         │  decisions)     │     │
│                                         └───────┬────────┘     │
│                                                 │              │
│                                    ┌────────────┴───────────┐  │
│                                    │  Export: JSON / PDF     │  │
│                                    └────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Component Details

| Component | Model / Tool | Details |
|-----------|-------------|---------|
| **Speech-to-Text** | OpenAI Whisper | Transformer-based encoder-decoder. Trained on 680k hours of multilingual audio. Converts speech → text locally. |
| **Whisper (base)** | 74M parameters | 6 encoder + 6 decoder layers. Fast (~30s for 1 min audio). ~139 MB. |
| **Whisper (medium)** | 769M parameters | 24 encoder + 24 decoder layers. More accurate. ~1.5 GB. |
| **LLM (local)** | LLaMA 3.2 (3B) | Meta's 3-billion parameter model via Ollama. Extracts structured JSON from transcript. ~2 GB. |
| **LLM (cloud)** | Google Gemini Flash | Optional cloud fallback. Requires API key. |
| **Frontend** | Streamlit 1.41 | Python-based web UI. Browser handles mic via WebRTC. |
| **PDF Export** | fpdf2 | Generates formatted PDF reports from structured JSON. |

### Data Flow

```
1. AUDIO INPUT
   Browser mic (WebRTC) → WAV file (48kHz, 16-bit PCM, mono)
   
2. TRANSCRIPTION (Whisper)
   WAV → Log-Mel Spectrogram → Encoder (Transformer) → Decoder → Text
   Model cached in ~/.cache/whisper/ after first download
   
3. STRUCTURED EXTRACTION (LLM)
   Transcript + Prompt → Ollama API (localhost:11434) → JSON response
   Prompt engineering extracts: summary, action_items[], decisions[]
   
4. EXPORT
   JSON dict → PDF (fpdf2) + JSON download
```

---

## How It Works

```
Record Audio → Whisper (speech-to-text) → LLM (structured extraction) → Meeting Minutes
```

| Step | Tool | Runs On |
|------|------|---------|
| 1. Record / Upload | Browser mic via `st.audio_input` | Browser |
| 2. Transcribe | OpenAI Whisper (base/medium) | Local CPU |
| 3. Generate Minutes | Ollama (llama3.2) or Gemini | Local / Cloud |
| 4. Export | JSON + PDF download | Browser |

---

## Project Structure

```
AI_MOM_Generater/
├── app.py              # Streamlit UI (main entry point)
├── audio_recorder.py   # Saves browser audio to WAV
├── speech_to_text.py   # Whisper transcription
├── llm_processor.py    # Ollama / Gemini integration
├── utils.py            # JSON export, PDF generation
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
├── Dockerfile          # Container build
├── docker-compose.yml  # Container orchestration
└── outputs/            # Generated files (gitignored)
```

---

## Using Gemini Instead of Ollama (Optional)

If you prefer a cloud LLM:

```bash
cp .env.example .env
# Edit .env and add your Google API key:
# GOOGLE_API_KEY=your_key_here
```

Get a free key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey). Then select **"Gemini (Cloud)"** in the sidebar.

---

## Docker

```bash
docker-compose up --build
```

> **Note:** Microphone recording requires browser mic access. Ollama must be running on the host machine.

---

## Output Format

The LLM generates structured JSON:

```json
{
  "summary": "Brief meeting summary...",
  "action_items": [
    {
      "person": "Rahul",
      "task": "Finalize UI design",
      "deadline": "Friday"
    }
  ],
  "decisions": [
    "Approved the new design system"
  ]
}
```

---

## Tech Stack

- **Frontend:** Streamlit
- **Speech-to-Text:** OpenAI Whisper (local)
- **LLM:** Ollama with llama3.2 (local, default) / Google Gemini (cloud, optional)
- **PDF Export:** fpdf2
- **Audio:** Browser WebRTC via `st.audio_input`

---

## Requirements

- Python 3.11+
- ffmpeg (installed via conda)
- Ollama ([ollama.com](https://ollama.com))
- ~4GB disk for models (Whisper base + llama3.2)

## License

MIT
