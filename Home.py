import sys
from pathlib import Path
from textwrap import dedent

import streamlit as st

#  Safe dotenv import
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If python-dotenv isn't available, just skip .env loading
    pass

#  MUST be called once, before any other st.* calls
st.set_page_config(page_title="Enginuity AI", page_icon="⚙️", layout="wide")

# For local imports
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Import after sys.path tweak
from ui.theme import load_css

#  Load CSS directly from file
css_file = ROOT / "ui" / "theme" / "base.css"
if css_file.exists():
    with open(css_file) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
else:
    st.error("ui/theme/base.css not found")

# If load_css expects a filename under ui/theme
load_css("base.css")

# --- Optional: simple debug marker so we know the app reached here ---
# st.write(" App booted – main layout loaded")

# --- Extra styling: CTA button + footer + no scroll ---
st.markdown(
    """
    <style>
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

      html, body, [data-testid="stAppViewContainer"] {
        height: 100%;
        overflow: hidden;
      }

      [data-testid="stMain"] .block-container {
        padding-top: 2rem;
        padding-bottom: 4rem;
      }

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

def main():
    # --- Hero Banner ---
    st.markdown(
        dedent("""
        <section class="hero">
          <h1>⚙️ Enginuity AI</h1>
          <p>
            Transform engineering lectures into structured, accessible study notes.<br>
            Upload audio, slides, or PDFs and get transcripts, formulas, code highlights, quizzes, and an AI chatbot.
          </p>
          <a href="pages/10_Upload.py" target="_self" class="cta-btn">🚀 Get Started</a>
        </section>
        """),
        unsafe_allow_html=True,
    )

    # --- Features Grid ---
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

    # --- Footer (optional) ---
    st.markdown(
        """
        <div class="eng-footer">
          © 2025 Enginuity AI – Built for engineering students
        </div>
        """,
        unsafe_allow_html=True,
    )

if __name__ == "__main__":
    main()
