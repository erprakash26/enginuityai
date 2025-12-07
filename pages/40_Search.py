# 40_Search.py 

import sys
from pathlib import Path
import re
import json
import os
from datetime import datetime
from typing import Dict

# --- Path setup ---
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Try to import httpx, but don't crash if it's missing
try:
    import httpx  # type: ignore
except ImportError:
    httpx = None  # type: ignore

import streamlit as st
from ui.bootstrap import ensure_corpus
from ui.theme import load_css

# --- Page setup ---
# st.set_page_config(page_title="Search", page_icon="🔍", layout="wide")
load_css("base.css")

ready = ensure_corpus()
if not ready:
    st.warning("No saved corpus found. Upload and process a lecture to search.")
    try:
        st.page_link("pages/Upload.py", label="Go to Upload", icon="📤")
    except Exception:
        pass
    # You may still allow keyword-only search against local file if you want
    # st.stop()

if not st.session_state.get("has_corpus"):
    st.warning("Upload and process a lecture to search.")
    try:
        st.page_link("pages/Upload.py", label="Go to Upload", icon="📤")
    except Exception:
        pass
    st.stop()

st.markdown('<div class="search-page">', unsafe_allow_html=True)
st.title("Search Notes")

# --- Metadata ---
DATA_DIR = Path("data")
NOTES_JSON = DATA_DIR / "notes.json"
lecture_title = "Notes"
if NOTES_JSON.exists():
    try:
        notes_doc = json.loads(NOTES_JSON.read_text(encoding="utf-8"))
        lecture_title = notes_doc.get("lecture_title", lecture_title)
        ts = notes_doc.get("generated_at")
        if ts:
            st.caption(
                f"Lecture: **{lecture_title}** · Generated: "
                f"{datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')}"
            )
    except Exception:
        st.caption(f"Lecture: **{lecture_title}**")

# --- Search controls ---
with st.form("search_form", clear_on_submit=False):
    q = st.text_input("Enter search query", placeholder="e.g., Laplace stability condition")
    colA, colB, colC = st.columns([1, 1, 1])
    top_k = colA.slider("Results", 3, 15, 5)
    mode = colB.selectbox("Mode", ["Hybrid", "Keyword", "Semantic"])
    show_snippets = colC.toggle("Show snippets", value=True)
    submitted = st.form_submit_button("Search", use_container_width=False)

# --- Mode mapping ---
mode_map: Dict[str, str] = {
    "Hybrid": "hybrid",
    "Keyword": "keyword",
    "Semantic": "semantic",
}
FASTAPI_URL = os.getenv("FASTAPI_URL", "http://127.0.0.1:8000")

# --- Run search ---
if submitted:
    q_clean = q.strip()
    if not q_clean:
        st.warning("Please enter a query.")
    else:
        sel_mode: str = mode_map.get(mode, "hybrid")

        try:
            if httpx is not None and FASTAPI_URL:
                with st.spinner("Searching…"):
                    resp = httpx.post(
                        f"{FASTAPI_URL}/search",
                        json={"q": q_clean, "top_k": int(top_k), "mode": sel_mode},
                        timeout=30.0,
                    )
                    resp.raise_for_status()
                    st.session_state["search_hits"] = resp.json()
            else:
                # Force fallback if httpx is missing or FASTAPI_URL empty
                raise RuntimeError("Backend search not available (httpx or FASTAPI_URL missing)")
        except Exception as e:
            st.error(f"Search failed or backend unavailable, showing demo results. ({e})")
            # graceful fallback
            st.session_state["search_hits"] = [
                {
                    "title": "Laplace Transform — definition",
                    "snippet": "The Laplace transform of f(t) is defined as 𝓛{f(t)} = ∫₀^∞ f(t)e^{-st} dt.",
                    "score": 0.82,
                    "section_id": "sec-2",
                    "source": lecture_title,
                },
                {
                    "title": "Poles & stability",
                    "snippet": "A linear system is stable if all poles lie strictly in the left half-plane.",
                    "score": 0.77,
                    "section_id": "sec-1",
                    "source": lecture_title,
                },
            ]

# --- Render results ---
hits = st.session_state.get("search_hits", [])


def highlight(text: str, query: str) -> str:
    if not query or not text:
        return text or ""
    try:
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        return pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", text)
    except re.error:
        return text


if hits:
    st.subheader("Results")
    for i, h in enumerate(hits, 1):
        title = h.get("title", "Untitled")
        snippet = h.get("snippet", "")
        score = float(h.get("score", 0.0))
        section_id = h.get("section_id")
        source = h.get("source", lecture_title)

        st.markdown(
            f"""
            <div class="result-card">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <h4 style="margin:0;">{i}. {title}</h4>
                <span class="score">{score:.2f}</span>
              </div>
              <div class="meta">
                Source: {source}{f" · Section: {section_id}" if section_id else ""}
              </div>
              {"<p>"+ highlight(snippet, q) +"</p>" if show_snippets and snippet else ""}
            </div>
            """,
            unsafe_allow_html=True,
        )

        a1, a2, a3 = st.columns([1, 1, 6])
        with a1:
            st.button("Open in Notes", key=f"open-{i}")
        with a2:
            st.button("Copy citation", key=f"cite-{i}")
else:
    st.info("Type a query and press **Search** to see results.")
    st.caption(
        'Tips: try concept names ("Laplace"), code terms ("numpy linspace"), '
        'or questions ("how to check stability").'
    )

st.markdown("</div>", unsafe_allow_html=True)
