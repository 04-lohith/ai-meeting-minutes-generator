"""
app.py — Streamlit UI for the AI Meeting Minutes Generator.

Clean, step-based design applying:
  - Hick's Law (fewer choices per step)
  - Fitts' Law (large, obvious CTA buttons)
  - Visual hierarchy (clear typographic scale)
  - Progressive disclosure (reveal complexity as needed)

Run with:
    streamlit run app.py
"""

import json
import streamlit as st
from audio_recorder import save_audio_bytes
from speech_to_text import transcribe_audio
from llm_processor import generate_minutes, _ollama_available, _ollama_models
from utils import save_json, generate_pdf, format_timestamp

# ── Page config ─────────────────────────────────────────────────

st.set_page_config(
    page_title="MinuteMaster AI",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Design System — Custom CSS ──────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, sans-serif;
}

/* ─── Pure Black ──────────────────────────────────── */
.stApp { background: #000; }

section[data-testid="stSidebar"] {
    background: #000;
    border-right: 1px solid #1a1a1a;
}
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stTextInput label {
    color: #666 !important;
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
header[data-testid="stHeader"] { background: transparent; }

/* ─── Brand ───────────────────────────────────────── */
.brand { text-align: center; padding: 1.5rem 0 0.5rem; }
.brand h1 {
    font-size: 1.6rem; font-weight: 700; color: #fff;
    letter-spacing: -0.03em; margin: 0;
}
.brand p { color: #555; font-size: 0.85rem; margin: 0.2rem 0 0; }

/* ─── Steps ───────────────────────────────────────── */
.step { display:flex; align-items:flex-start; gap:0.8rem; margin:2rem 0 0.6rem; }
.step-num {
    width:24px; height:24px; border-radius:6px; background:#1a1a1a;
    color:#888; font-size:0.8rem; font-weight:600;
    display:flex; align-items:center; justify-content:center;
    flex-shrink:0; margin-top:2px; border:1px solid #222;
}
.step-num.done { background:#111; color:#4ade80; border-color:#1a3a1a; }
.step-label { font-size:1rem; font-weight:600; color:#e0e0e0; }
.step-desc { font-size:0.8rem; color:#555; margin-top:1px; }

/* ─── Result Cards ────────────────────────────────── */
.result-card {
    background: #0a0a0a; border:1px solid #1a1a1a;
    border-radius:8px; padding:1.2rem 1.4rem; margin-bottom:0.8rem;
}
.result-card h4 {
    color:#999; font-weight:600; font-size:0.75rem; margin:0 0 0.5rem;
    text-transform:uppercase; letter-spacing:0.06em;
}
.result-card p { color:#ccc; font-size:0.9rem; line-height:1.7; margin:0; }

/* ─── Table ───────────────────────────────────────── */
.items-table { width:100%; border-collapse:collapse; }
.items-table th {
    color:#555; padding:0.5rem 0.8rem; text-align:left;
    font-weight:600; font-size:0.7rem; text-transform:uppercase;
    letter-spacing:0.06em; border-bottom:1px solid #1a1a1a;
}
.items-table td {
    padding:0.55rem 0.8rem; color:#ccc;
    border-bottom:1px solid #111; font-size:0.88rem;
}
.items-table tr:last-child td { border-bottom:none; }
.items-table .person { font-weight:600; color:#fff; }
.items-table .deadline { color:#888; font-size:0.82rem; }

/* ─── Tags ────────────────────────────────────────── */
.tag {
    display:inline-block; background:#111; border:1px solid #222;
    color:#aaa; padding:0.35rem 0.75rem; border-radius:4px;
    margin:0.2rem 0.25rem 0.2rem 0; font-size:0.82rem;
}

/* ─── Buttons ─────────────────────────────────────── */
.stButton > button {
    border-radius:6px; font-weight:600; font-family:'Inter',sans-serif;
    transition: opacity 0.15s;
}
.stButton > button:hover { opacity:0.85; }
.stDownloadButton > button {
    border-radius:6px; font-weight:600; font-family:'Inter',sans-serif;
}

/* ─── Misc ────────────────────────────────────────── */
.divider { height:1px; background:#1a1a1a; margin:1.2rem 0; }
.pill {
    display:inline-flex; align-items:center; gap:0.3rem;
    padding:0.25rem 0.6rem; border-radius:100px;
    font-size:0.72rem; font-weight:500;
}
.pill-done { background:#0a1a0a; color:#4ade80; border:1px solid #1a2a1a; }
.footer { text-align:center; color:#333; font-size:0.7rem; padding:2rem 0 1rem; }
</style>
""", unsafe_allow_html=True)


# ── Session state ───────────────────────────────────────────────

for key, default in [
    ("audio_path", None), ("transcript", ""),
    ("minutes", None), ("status", "idle"),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ── Sidebar — Settings ──────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="text-align:center; margin-bottom:1.5rem;">
        <span style="font-size:2rem;">📋</span>
        <p style="color:#c7d2fe; font-size:1.1rem; font-weight:700;
                  margin:0.3rem 0 0; letter-spacing:-0.01em;">MinuteMaster AI</p>
        <p style="color:#475569; font-size:0.75rem; margin:0.2rem 0 0;">
            Local-first meeting intelligence</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # LLM Provider
    llm_provider = st.selectbox(
        "LLM PROVIDER",
        ["Ollama (Local)", "Gemini (Cloud)"],
        index=0,
    )
    use_ollama = llm_provider.startswith("Ollama")

    api_key = None
    ollama_model = "llama3.2"

    if use_ollama:
        ollama_ok = _ollama_available()
        if ollama_ok:
            models = _ollama_models()
            if models:
                ollama_model = st.selectbox("OLLAMA MODEL", models, index=0)
            st.markdown(
                '<span class="pill pill-done">● Connected</span>',
                unsafe_allow_html=True,
            )
        else:
            st.error("Ollama offline — run `ollama serve`")
    else:
        api_key = st.text_input("API KEY", type="password")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    whisper_model = st.selectbox(
        "WHISPER MODEL",
        ["base", "small", "medium", "large"],
        index=0,
    )

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.markdown("""
    <div style="padding:0.8rem; background:rgba(99,102,241,0.06);
                border-radius:8px; border:1px solid rgba(99,102,241,0.1);">
        <p style="color:#94a3b8; font-size:0.78rem; margin:0; line-height:1.6;">
            <strong style="color:#c7d2fe;">Quick start:</strong><br>
            ① Record or upload audio<br>
            ② Transcribe with Whisper<br>
            ③ Generate minutes with AI<br>
            ④ Export as JSON or PDF
        </p>
    </div>
    """, unsafe_allow_html=True)


# ── Brand Header ────────────────────────────────────────────────

st.markdown("""
<div class="brand">
    <h1>📋 MinuteMaster AI</h1>
    <p>Record · Transcribe · Summarise — powered by Whisper & {provider}</p>
</div>
""".format(provider="Ollama" if use_ollama else "Gemini"), unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# STEP 1 — Audio Input
# ═══════════════════════════════════════════════════════════════

step1_done = st.session_state.audio_path is not None or bool(st.session_state.transcript)
step1_class = "done" if step1_done else ""

st.markdown(f"""
<div class="step">
    <div class="step-num {step1_class}">{"✓" if step1_done else "1"}</div>
    <div>
        <div class="step-label">Capture Meeting Audio</div>
        <div class="step-desc">Record live, upload a file, or paste a transcript directly</div>
    </div>
</div>
""", unsafe_allow_html=True)

tab_record, tab_upload, tab_paste = st.tabs([
    "🎙 Record", "📁 Upload", "📋 Paste Transcript"
])

audio_bytes = None

with tab_record:
    audio_data = st.audio_input(
        "Record your meeting",
        label_visibility="collapsed",
    )
    if audio_data is not None:
        audio_bytes = audio_data.getvalue()

with tab_upload:
    uploaded = st.file_uploader(
        "Drop your audio file here",
        type=["wav", "mp3", "m4a", "ogg", "flac", "webm"],
        label_visibility="collapsed",
    )
    if uploaded is not None:
        audio_bytes = uploaded.getvalue()

with tab_paste:
    pasted = st.text_area(
        "Paste transcript",
        height=160,
        placeholder="Rahul: Let's finalize the UI design by Friday.\n"
                    "Priya: I will send the updated wireframes tomorrow.\n"
                    "Manager: Let's schedule client review next Monday.",
        label_visibility="collapsed",
    )
    if pasted.strip():
        if st.button("✓ Use This Transcript", use_container_width=True, type="primary"):
            st.session_state.transcript = pasted.strip()
            st.session_state.minutes = None
            st.rerun()

if audio_bytes:
    path = save_audio_bytes(audio_bytes)
    st.session_state.audio_path = path
    st.caption(f"✅ Audio captured — {len(audio_bytes)/1024:.0f} KB")


# ═══════════════════════════════════════════════════════════════
# STEP 2 — Transcription
# ═══════════════════════════════════════════════════════════════

step2_done = bool(st.session_state.transcript)
step2_class = "done" if step2_done else ""

st.markdown(f"""
<div class="step">
    <div class="step-num {step2_class}">{"✓" if step2_done else "2"}</div>
    <div>
        <div class="step-label">Transcribe</div>
        <div class="step-desc">Convert speech to text with Whisper, then review</div>
    </div>
</div>
""", unsafe_allow_html=True)

has_audio = st.session_state.audio_path is not None

if has_audio and not st.session_state.transcript:
    if st.button("📝 Transcribe with Whisper", use_container_width=True, type="primary"):
        with st.spinner(f"Transcribing with Whisper ({whisper_model}) …"):
            try:
                result = transcribe_audio(
                    st.session_state.audio_path, model_size=whisper_model,
                )
                if result.strip():
                    st.session_state.transcript = result
                    st.session_state.minutes = None
                    st.rerun()
                else:
                    st.warning(
                        "Whisper found no speech in the audio. Your browser mic "
                        "may not be capturing properly. Try the **Paste Transcript** "
                        "tab instead, or check mic permissions."
                    )
            except Exception as e:
                st.error(f"Transcription failed: {e}")

elif not has_audio and not st.session_state.transcript:
    st.caption("Waiting for audio input from Step 1 …")

if st.session_state.transcript:
    edited = st.text_area(
        "Edit transcript",
        value=st.session_state.transcript,
        height=180,
        label_visibility="collapsed",
    )
    st.session_state.transcript = edited

    if st.button("↺ Clear & start over", type="secondary"):
        st.session_state.transcript = ""
        st.session_state.minutes = None
        st.session_state.audio_path = None
        st.rerun()


# ═══════════════════════════════════════════════════════════════
# STEP 3 — Generate Minutes
# ═══════════════════════════════════════════════════════════════

step3_done = st.session_state.minutes is not None
step3_class = "done" if step3_done else ""

st.markdown(f"""
<div class="step">
    <div class="step-num {step3_class}">{"✓" if step3_done else "3"}</div>
    <div>
        <div class="step-label">Generate Meeting Minutes</div>
        <div class="step-desc">AI extracts summary, action items, and key decisions</div>
    </div>
</div>
""", unsafe_allow_html=True)

can_generate = bool(st.session_state.transcript) and not st.session_state.minutes

if can_generate:
    provider_name = "Ollama" if use_ollama else "Gemini"
    if st.button(
        f"✨ Generate with {provider_name}",
        use_container_width=True,
        type="primary",
    ):
        with st.spinner(f"Generating minutes with {provider_name} …"):
            try:
                mins = generate_minutes(
                    st.session_state.transcript,
                    api_key=api_key,
                    provider="ollama" if use_ollama else "gemini",
                    ollama_model=ollama_model,
                )
                st.session_state.minutes = mins
                st.session_state.status = "done"
                save_json(mins)
                st.rerun()
            except (ValueError, RuntimeError) as e:
                st.error(f"⚠️ {e}")
            except Exception as e:
                st.error(f"⚠️ Unexpected error: {e}")


# ═══════════════════════════════════════════════════════════════
# Results Display
# ═══════════════════════════════════════════════════════════════

if st.session_state.minutes:
    data = st.session_state.minutes

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # ── Summary ─────────────────────────────────────
    st.markdown(f"""
    <div class="result-card">
        <h4>📋 Meeting Summary</h4>
        <p>{data.get('summary', 'N/A')}</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Action Items ────────────────────────────────
    action_items = data.get("action_items", [])
    if action_items:
        rows = ""
        for item in action_items:
            rows += (
                f'<tr>'
                f'<td class="person">{item.get("person", "—")}</td>'
                f'<td>{item.get("task", "—")}</td>'
                f'<td class="deadline">{item.get("deadline", "—")}</td>'
                f'</tr>'
            )
        st.markdown(f"""
        <div class="result-card">
            <h4>🎯 Action Items</h4>
            <table class="items-table">
                <thead><tr><th>Person</th><th>Task</th><th>Deadline</th></tr></thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
        """, unsafe_allow_html=True)

    # ── Decisions ───────────────────────────────────
    decisions = data.get("decisions", [])
    st.markdown('<div class="result-card"><h4>⚖️ Key Decisions</h4>', unsafe_allow_html=True)
    if decisions:
        tags = "".join(f'<span class="tag">{d}</span>' for d in decisions)
        st.markdown(tags, unsafe_allow_html=True)
    else:
        st.caption("No decisions identified.")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Raw JSON ────────────────────────────────────
    with st.expander("View Raw JSON"):
        st.json(data)

    # ── Export ──────────────────────────────────────
    st.markdown("""
    <div class="step">
        <div class="step-num done">↓</div>
        <div><div class="step-label">Export</div></div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    ts = format_timestamp().replace(" ", "_").replace(",", "")

    with col1:
        st.download_button(
            "⬇ Download JSON",
            data=json.dumps(data, indent=2, ensure_ascii=False),
            file_name=f"minutes_{ts}.json",
            mime="application/json",
            use_container_width=True,
        )

    with col2:
        try:
            pdf_path = generate_pdf(data)
            with open(pdf_path, "rb") as f:
                st.download_button(
                    "⬇ Download PDF",
                    data=f.read(),
                    file_name=f"minutes_{ts}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
        except Exception as e:
            st.error(f"PDF error: {e}")

    # Reset for new meeting
    if st.button("🔄 New Meeting", use_container_width=True):
        for k in ("audio_path", "transcript", "minutes", "status"):
            st.session_state[k] = None if k != "transcript" else ""
        st.session_state.status = "idle"
        st.rerun()


# ── Footer ──────────────────────────────────────────────────────

st.markdown(
    '<div class="footer">MinuteMaster AI · Whisper · {p} · Built with Streamlit</div>'
    .format(p="Ollama" if use_ollama else "Gemini"),
    unsafe_allow_html=True,
)
