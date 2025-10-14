import sys
from pathlib import Path
from textwrap import dedent
import streamlit as st
from ui.theme import load_css
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(page_title="Enginuity AI", page_icon="⚙️", layout="wide")

# Load CSS directly
css_file = Path("ui/theme/base.css")
if css_file.exists():
    with open(css_file) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
else:
    st.error("base.css not found")

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_css("base.css")

# --- Style only for Get Started + footer + no scroll ---
st.markdown(
    """
    <style>
      /* Make only the Get Started CTA clearer */
      .cta-btn {
        display: inline-block;
        padding: 0.9rem 2rem;
        font-size: 1.1rem;
        font-weight: 600;
        background-color: #2563eb;
        color: #ffffff !important;
        border-radius: 8px;
        text-decoration: none;
        border: none;
        transition: background 0.2s ease, transform 0.2s ease;
      }
      .cta-btn:hover {
        background-color: #1d4ed8;
        transform: translateY(-2px);
      }

      /* Prevent scrolling */
      html, body, [data-testid="stAppViewContainer"] {
        height: 100%;
        overflow: hidden;
      }

      /* Main container adjustments for footer space */
      [data-testid="stMain"] .block-container {
        padding-top: 2rem;
        padding-bottom: 4rem;
      }

      /* Footer (no background) */
      .eng-footer {
        position: fixed;
        left: 0;
        right: 0;
        bottom: 0;
        padding: 8px;
        text-align: center;
        font-size: 0.9rem;
        color: #64748b;
      }
      [data-theme="dark"] .eng-footer {
        color: #94a3b8;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Hero Banner (clean, no demo box) ---
st.markdown(
    dedent("""
    <section class="hero">
      <h1>⚙️ Enginuity AI</h1>
      <p>
        Transform engineering lectures into structured, accessible study notes.  
        Upload audio, slides, or PDFs and get transcripts, formulas, code highlights, quizzes, and an AI chatbot.
      </p>
      <a href="pages/10_Upload.py" target="_self" class="cta-btn">🚀 Get Started</a>
    </section>
    """),
    unsafe_allow_html=True,
)

# --- Features Grid (unchanged) ---
st.markdown(
    dedent("""
    <section class="features">
      <div class="features-grid">
        <div class="card"><div class="icon">📤</div><a href="pages/10_Upload.py">Upload</a></div>
        <div class="card"><div class="icon">📓</div><a href="pages/30_Notes.py">Notes</a></div>
        <div class="card"><div class="icon">🔍</div><a href="pages/40_Search.py">Search</a></div>
        <div class="card"><div class="icon">🧩</div><a href="pages/50_Quiz.py">Quiz</a></div>
        <div class="card"><div class="icon">🤖</div><a href="pages/60_Chat.py">Ask AI</a></div>
        <div class="card"><div class="icon">🧪</div><a href="./?demo=1">Sample Lecture</a></div>
      </div>
    </section>
    """),
    unsafe_allow_html=True,
)

