# notes.py
import sys
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional
from ui.bootstrap import ensure_corpus

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from ui.theme import load_css

# Try to import httpx, but don't crash if it's missing
try:
    import httpx  # type: ignore
except ImportError:
    httpx = None  # type: ignore

# IMPORTANT: set_page_config should be called only once in the main entry page.
# st.set_page_config(page_title="Notes", page_icon="📓", layout="wide")

load_css("base.css")
ready = ensure_corpus()

if not ready:
    st.warning("No saved notes found yet. Upload and process a lecture to view notes.")
    try:
        st.page_link("pages/Upload.py", label="Go to Upload", icon="📤")
    except Exception:
        pass
    # You can still show local fallback/sample below if you want, instead of st.stop()
    # st.stop()

if not st.session_state.get("has_corpus"):
    st.warning("Upload and process a lecture to view notes.")
    try:
        st.page_link("pages/Upload.py", label="Go to Upload", icon="📤")
    except Exception:
        pass
    st.stop()

st.markdown('<div class="notes-page">', unsafe_allow_html=True)
st.title("Lecture Notes")

DATA_DIR = Path("data")
NOTES_JSON = DATA_DIR / "notes.json"   # optional local fallback
META_JSON = DATA_DIR / "uploads.json"  # optional: to show context/source
FASTAPI_URL = os.getenv("FASTAPI_URL", "http://127.0.0.1:8000")

def _local_sample() -> Dict[str, Any]:
    return {
        "lecture_title": "Sample Notes",
        "generated_at": int(datetime.now().timestamp()),
        "sections": [
            {"id": "sec-1", "title": "Signals & Systems", "type": "text",
             "content": "Definition, block diagrams, linearity, time-invariance…"},
            {"id": "sec-2", "title": "Laplace Transform", "type": "latex",
             "content": r"$$\mathcal{L}\{f(t)\} = \int_0^\infty f(t)e^{-st} dt$$"},
            {"id": "sec-3", "title": "Example Code", "type": "code", "language": "python",
             "content": "import numpy as np\nt = np.linspace(0,1,1000)\n"},
        ],
    }

def load_notes() -> Dict[str, Any]:
    """
    Tries the backend first (GET /notes) if httpx is available.
    Falls back to local notes.json if present, otherwise returns a small in-memory sample.
    """
    # 1) Backend – only if httpx & FASTAPI_URL available
    if httpx is not None and FASTAPI_URL:
        try:
            with st.spinner("Loading notes from backend…"):
                r = httpx.get(f"{FASTAPI_URL}/notes", timeout=15.0)
                r.raise_for_status()
                doc = r.json()
                if isinstance(doc, dict) and doc.get("sections"):
                    return doc
        except Exception:
            # If backend fails, fall through to local/sample
            pass

    # 2) Local file
    if NOTES_JSON.exists():
        try:
            return json.loads(NOTES_JSON.read_text(encoding="utf-8"))
        except Exception:
            pass

    # 3) Sample
    return _local_sample()

notes: Dict[str, Any] = load_notes()
sections: List[Dict[str, Any]] = notes.get("sections", [])
lecture_title: str = str(notes.get("lecture_title", "Untitled"))
generated_at: Optional[int] = notes.get("generated_at")

# Header metadata
cols = st.columns([3, 2, 1])
with cols[0]:
    st.caption(f"Lecture: **{lecture_title}**")
with cols[1]:
    if generated_at:
        try:
            ts = datetime.fromtimestamp(int(generated_at)).strftime("%Y-%m-%d %H:%M")
            st.caption(f"Generated: **{ts}**")
        except Exception:
            pass
with cols[2]:
    # Download full markdown export (simple join)
    md_export = "# " + lecture_title + "\n\n" + "\n\n".join(
        [f"## {s.get('title','Untitled')}\n\n{s.get('content','')}" for s in sections]
    )
    st.download_button("Download .md", data=md_export, file_name="lecture-notes.md")

left, right = st.columns([1, 3], gap="large")

with left:
    st.markdown('<div class="sticky-left">', unsafe_allow_html=True)
    st.subheader("Contents")

    # Search filter
    q = (st.text_input("Search", placeholder="Filter sections…") or "").strip().lower()
    filtered = [
        s for s in sections
        if (q in (s.get("title","").lower()) or q in (s.get("content","").lower()))
    ] if q else sections

    # Radio to select section
    if filtered:
        options = [s.get("title", "Untitled") for s in filtered]
        selected_title = st.radio(
            "Sections",
            options=options,
            label_visibility="collapsed",
            index=0
        )
        # Map back to section object
        selected = next((s for s in filtered if s.get("title") == selected_title), None)
    else:
        st.info("No sections match your search.")
        selected = None

    st.markdown('</div>', unsafe_allow_html=True)

with right:
    if selected:
        st.markdown(f"### {selected.get('title','Untitled')}")
        s_type = selected.get("type", "text")
        content = selected.get("content", "")

        if s_type == "code":
            lang = selected.get("language", None)
            st.code(content, language=lang)
        elif s_type == "latex":
            st.markdown(content)
        else:
            st.markdown(content)

        # Actions row
        a1, a2, _ = st.columns([1, 1, 6])
        with a1:
            if st.button("🔊 Read aloud"):
                st.info("TTS will be available once connected to the backend.")
        with a2:
            st.download_button(
                "⬇️ Save section",
                data=content if s_type != "code" else f"```{selected.get('language','')}\n{content}\n```",
                file_name=f"{str(selected.get('title','Section')).replace(' ','_')}.md"
            )

st.markdown('</div>', unsafe_allow_html=True)
