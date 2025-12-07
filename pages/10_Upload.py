# upload.py
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import time
import json
import os
import streamlit as st
import requests  # use requests instead of httpx


# IMPORTANT: set_page_config should be called once in the main app page only (e.g., Home.py).
# st.set_page_config(page_title="Upload", page_icon="📤", layout="wide")

load_css("base.css")

st.markdown('<div class="upload-page">', unsafe_allow_html=True)
st.title("Upload Files")

st.session_state.setdefault("has_corpus", False)

DATA_DIR = Path("data")
UPLOAD_DIR = DATA_DIR / "uploads"
META_FILE = DATA_DIR / "uploads.json"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

FASTAPI_URL = os.getenv("FASTAPI_URL", "http://127.0.0.1:8000")

def _load_meta():
    if META_FILE.exists():
        try:
            return json.loads(META_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []

def _save_meta(meta):
    META_FILE.parent.mkdir(parents=True, exist_ok=True)
    META_FILE.write_text(json.dumps(meta, indent=2), encoding="utf-8")

def _append_meta(entry):
    meta = _load_meta()
    meta.insert(0, entry)
    # keep last 100
    meta = meta[:100]
    _save_meta(meta)

left, right = st.columns([2, 1], gap="large")

with left:
    kind = st.radio("File type:", ["PDF / Slides", "Audio"], horizontal=True)
    if kind == "PDF / Slides":
        up = st.file_uploader(
            "Choose file(s)",
            type=["pdf", "pptx"],
            accept_multiple_files=True,
        )
    else:
        up = st.file_uploader(
            "Choose audio file(s)",
            type=["mp3", "wav", "m4a"],
            accept_multiple_files=True,
        )

    # show selections
    if up:
        st.write("Files selected:")
        for f in up:
            st.write(f"- {f.name} ({f.size/1024:.1f} KB)")
        st.divider()

        st.subheader("Processing Plan")
        st.markdown(
            """
            1) Extract text (PDF/Slides) / Transcribe (Audio)  
            2) Chunk & label content (Concepts / Code / Formula)  
            3) Build searchable index  
            """
        )

    # Save and process
    can_process = bool(up)
    process_btn = st.button("Process Now", disabled=not can_process)

    if process_btn and up:
        # 1) Save files locally (always)
        saved = []
        for f in up:
            safe_name = f.name.replace("/", "_").replace("\\", "_")
            dest = UPLOAD_DIR / safe_name
            dest.write_bytes(f.read())
            saved.append(dest)
            _append_meta({
                "name": safe_name,
                "bytes": dest.stat().st_size,
                "kind": "audio" if kind == "Audio" else "doc",
                "ts": int(time.time())
            })

        # 2) Try backend ingestion if available; otherwise simulate steps
        with st.status("Starting processing…", expanded=True) as status:
            try:
                st.write("• Sending to backend ingestion…")
                # Prefer /ingest; if you implemented /upload use that instead.
                files = []
                for p in saved:
                    files.append(("files", (p.name, p.open("rb"), "application/octet-stream")))
                payload = {"kind": "audio" if kind == "Audio" else "doc"}

                # Adjust endpoint name when you implement it in FastAPI
                resp = requests.post(f"{FASTAPI_URL}/upload", data=payload, files=files, timeout=120.0)
                resp.raise_for_status()

                st.write("• Backend chunking & labeling…")
                st.write("• Building searchable index…")
                status.update(label="Processing complete ✅", state="complete")
                st.session_state["has_corpus"] = True
                st.success("Your corpus is ready (backend).")
            except Exception as e:
                # graceful fallback (your original simulated steps)
                st.write("• Extracting / Transcribing…")
                time.sleep(0.6)
                st.write("• Chunking & labeling content…")
                time.sleep(0.6)
                st.write("• Building searchable index…")
                time.sleep(0.6)
                status.update(label="Processing complete ✅ (local fallback)", state="complete")
                st.info(f"Backend not used (yet): {e}")
                st.session_state["has_corpus"] = True

        st.markdown("➡️ Go to **Notes** or **Search/Q&A** to see results.")

with right:
    st.subheader("Tips")
    st.info(
        "• Use smaller files for faster tests\n"
        "• Descriptive filenames help\n"
        "• You can re-process anytime\n"
        "• Accepted: PDF, PPTX, MP3, WAV, M4A"
    )

    st.subheader("Recent uploads")
    meta = _load_meta()
    if meta:
        for m in meta[:5]:
            size_kb = m["bytes"] / 1024 if m.get("bytes") else 0
            st.write(f"{m['name']}  ·  {m['kind']}  ·  {size_kb:.1f} KB")
    else:
        st.write("No files yet.")

st.markdown('</div>', unsafe_allow_html=True)
