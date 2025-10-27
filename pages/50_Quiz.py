# quiz.py
import sys
from pathlib import Path
import json
import random
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from ui.bootstrap import ensure_corpus

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from ui.theme import load_css
import httpx  # NEW

# IMPORTANT: set_page_config should be called only once in the main entry page.
# st.set_page_config(page_title="Quiz", page_icon="🧩", layout="wide")

load_css("base.css")

ready = ensure_corpus()
if not ready:
    st.warning("No saved corpus found. Upload and process a lecture to generate quizzes.")
    try:
        st.page_link("pages/Upload.py", label="Go to Upload", icon="📤")
    except Exception:
        pass
    # You may continue; the page can still use local notes.json as fallback
    # st.stop()

# prefer backend-provided meta when available
if st.session_state.get("lecture_title"):
    lecture_title = st.session_state["lecture_title"]
if st.session_state.get("generated_at"):
    try:
        ts = int(st.session_state["generated_at"])
        st.caption(
            f"Lecture: **{lecture_title}** · Generated: "
            f"{datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')}"
        )
    except Exception:
        pass

if not st.session_state.get("has_corpus"):
    st.warning("Upload and process a lecture to generate quizzes.")
    try:
        st.page_link("pages/Upload.py", label="Go to Upload", icon="📤")
    except Exception:
        pass
    st.stop()

st.markdown('<div class="quiz-page">', unsafe_allow_html=True)
st.title("Quiz")

# ---------- Data paths ----------
DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

NOTES_JSON = DATA_DIR / "notes.json"
SNAPSHOTS_FILE = DATA_DIR / "quiz_snapshots.jsonl"
ATTEMPTS_FILE = DATA_DIR / "quiz_attempts.jsonl"

lecture_title = "Notes"
if NOTES_JSON.exists():
    try:
        doc = json.loads(NOTES_JSON.read_text(encoding="utf-8"))
        lecture_title = doc.get("lecture_title", lecture_title)
        ts = doc.get("generated_at")
        if ts:
            st.caption(
                f"Lecture: **{lecture_title}** · Generated: "
                f"{datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')}"
            )
    except Exception:
        pass

# ---------- Local history helpers (JSONL) ----------
def _now_iso() -> str:
    return datetime.now().isoformat()

def _append_jsonl(path: Path, obj: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    except Exception as e:
        st.warning(f"Could not write to {path.name}: {e}")

def save_quiz_snapshot(meta: dict, items: list) -> str:
    """Persist exactly what the user sees after Generate."""
    snapshot_id = str(uuid.uuid4())
    rec = {
        "snapshot_id": snapshot_id,
        "created_at": _now_iso(),
        "meta": meta,
        "items": items,
    }
    _append_jsonl(SNAPSHOTS_FILE, rec)
    return snapshot_id

def save_quiz_attempt(snapshot_id: Optional[str], meta: dict, review: list, started_at: str, submitted_at: str) -> str:
    """Persist a graded attempt with per-question review."""
    attempt_id = str(uuid.uuid4())
    score_raw = sum(1 for r in review if r.get("ok"))
    score_max = max(1, len(review))
    rec = {
        "attempt_id": attempt_id,
        "snapshot_id": snapshot_id,
        "lecture": meta.get("lecture"),
        "type": meta.get("type"),
        "difficulty": meta.get("difficulty"),
        "topic": meta.get("topic"),
        "started_at": started_at,
        "submitted_at": submitted_at,
        "saved_at": _now_iso(),
        "score_raw": score_raw,
        "score_max": score_max,
        "score_pct": round(100.0 * score_raw / score_max, 2),
        "items": review,
    }
    _append_jsonl(ATTEMPTS_FILE, rec)
    return attempt_id

def load_attempts(lecture: Optional[str] = None, limit: int = 20) -> list[dict]:
    """Read latest attempts (optionally filtered by lecture)."""
    if not ATTEMPTS_FILE.exists():
        return []
    rows: list[dict] = []
    try:
        with ATTEMPTS_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    if (lecture is None) or (obj.get("lecture") == lecture):
                        rows.append(obj)
                except Exception:
                    pass
        rows.sort(key=lambda r: r.get("submitted_at") or r.get("saved_at") or "", reverse=True)
        return rows[:limit]
    except Exception:
        return []

def load_snapshot(snapshot_id: str) -> Optional[dict]:
    """Find a snapshot by id from quiz_snapshots.jsonl."""
    if not snapshot_id or not SNAPSHOTS_FILE.exists():
        return None
    try:
        with SNAPSHOTS_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    if obj.get("snapshot_id") == snapshot_id:
                        return obj
                except Exception:
                    continue
    except Exception:
        pass
    return None

# ---------- Helpers ----------
def reset_attempt_state() -> None:
    st.session_state["quiz_answers"] = {}      # question_idx -> user answer (string)
    st.session_state["quiz_submitted"] = False
    st.session_state["quiz_score"] = None

def shuffle_choices(choices: List[str], answer: str):
    """Return (shuffled_choices, correct_index) while preserving the correct answer string."""
    if not choices:
        return [], None
    items = list(choices)
    random.shuffle(items)
    correct_index = items.index(answer) if answer in items else None
    return items, correct_index

def load_local_sections() -> List[Dict[str, Any]]:
    """Read sections from notes.json (used to scope quiz generation)."""
    if NOTES_JSON.exists():
        try:
            _doc = json.loads(NOTES_JSON.read_text(encoding="utf-8"))
            secs = _doc.get("sections", [])
            # keep only blocks that have content
            return [s for s in secs if s.get("content")]
        except Exception:
            return []
    return []

# ---------- Section scope (optional) ----------
all_sections = load_local_sections()
section_titles = [s.get("title", "Untitled") for s in all_sections]

with st.expander("Section scope (optional)"):
    picked_titles = st.multiselect(
        "Only generate questions from these sections",
        options=section_titles,
        default=section_titles[:4] if section_titles else []
    )
    picked = [s for s in all_sections if s.get("title", "Untitled") in picked_titles]

# ---------- Controls ----------
with st.form("quiz_controls"):
    c1, c2, c3 = st.columns([1, 1, 2])
    n_questions = c1.slider("Number of questions", 3, 25, 6)
    qtype = c2.selectbox("Type", ["MCQ", "Fill-in-the-blank", "Mix"])
    difficulty = c3.selectbox("Difficulty", ["Auto", "Easy", "Medium", "Hard"])
    topic_seed = st.text_input("Optional topic focus", placeholder="e.g., Laplace, stability, convolution")
    generated = st.form_submit_button("Generate Quiz")

FASTAPI_URL = (os.getenv("FASTAPI_URL", "http://127.0.0.1:8000") or "").rstrip("/")

# ---------- Generate via backend ----------
if generated:
    # Build scoped context from selected sections (or all sections if none picked)
    section_ids: List[str] = [s.get("id", "") for s in picked] if picked else []
    raw_context_parts: List[str] = []
    for s in (picked or all_sections):
        title = s.get("title", "")
        content = s.get("content", "")
        s_type = s.get("type", "text")
        if not content:
            continue
        if s_type == "code":
            raw_context_parts.append(f"{title}\nCode:\n{content}\n")
        elif s_type == "latex":
            raw_context_parts.append(f"{title}\nMath:\n{content}\n")
        else:
            raw_context_parts.append(f"{title}\n{content}\n")

    context_text = "\n\n".join(raw_context_parts).strip()

    # cap payload size to keep requests snappy
    if len(context_text) > 12000:
        context_text = context_text[:12000]

    # Guard: don't submit if there is no study text
    if not context_text.strip() and not (topic_seed and topic_seed.strip()):
        st.error("No study material found. Select relevant sections or provide a topic focus.")
        st.stop()

    # Small debug badge so you know what's being sent
    st.caption(f"Context chars: {len(context_text)}")

    payload: Dict[str, Any] = {
        "n": int(n_questions),
        "type": str((qtype or "MCQ")).lower(),
        "difficulty": str((difficulty or "Auto")).lower(),
        "topic": topic_seed or None,
        "section_ids": section_ids or None,
        "context": context_text or None,    # backend prefers this
        "corpus_id": st.session_state.get("corpus_id"),
        "lecture_title": lecture_title,
    }

    # normalize qtype to what backend expects
    if payload["type"] in ("fill-in-the-blank", "fill in the blank", "fill_in_the_blank"):
        payload["type"] = "fib"

    try:
        with st.spinner("Generating quiz…"):
            # Accept both /quiz and /quiz/ (router supports both)
            r = httpx.post(f"{FASTAPI_URL}/quiz", json=payload, timeout=60.0)
            r.raise_for_status()
            items_from_api: List[Dict[str, Any]] = r.json() or []
    except Exception as e:
        st.error(f"Quiz generation failed: {e}")
        items_from_api = []

    # Prepare a view-model with shuffled choices (don’t mutate originals)
    vm: List[Dict[str, Any]] = []
    for it in items_from_api:
        choices = it.get("choices", [])
        if choices:
            shuf, _ = shuffle_choices(choices, it.get("answer", ""))
            vm.append({**it, "choices_shuf": shuf})
        else:
            vm.append({**it, "choices_shuf": []})

    st.session_state["quiz_items"] = vm
    st.session_state["quiz_meta"] = {
        "lecture": lecture_title,
        "n": len(vm),
        "type": qtype,
        "difficulty": difficulty,
        "topic": topic_seed,
        "generated_at": datetime.now().isoformat(),
        "section_ids": section_ids,
    }
    # mark quiz start time
    st.session_state["quiz_started_at"] = datetime.now().isoformat()

    # Save a local snapshot of exactly what was generated (for history)
    snapshot_id = save_quiz_snapshot(meta=st.session_state["quiz_meta"], items=st.session_state["quiz_items"])
    st.session_state["quiz_snapshot_id"] = snapshot_id
    st.caption(f"Snapshot saved · id: `{snapshot_id[:8]}…`")

    reset_attempt_state()

items = st.session_state.get("quiz_items", [])
meta = st.session_state.get("quiz_meta", {})

if not items:
    st.info("Set your preferences above and click **Generate Quiz**.")
else:
    # ---------- Render Quiz ----------
    st.subheader(f"{meta.get('lecture','Notes')} · {meta.get('type','MCQ')} · {meta.get('difficulty','Auto')}")
    focus = f" · Focus: {meta['topic']}" if meta.get("topic") else ""
    st.caption(f"{meta.get('n', len(items))} questions{focus}")
    if meta.get("section_ids"):
        st.caption(f"Scoped to {len(meta['section_ids'])} section(s)")

    # Ensure a start timestamp if page re-renders
    if "quiz_started_at" not in st.session_state:
        st.session_state["quiz_started_at"] = datetime.now().isoformat()

    # Render each item
    for i, item in enumerate(items, 1):
        st.markdown("<div class='quiz-card'>", unsafe_allow_html=True)
        st.write(f"**{i}.** {item.get('q', '')}")

        # MCQ
        if item.get("choices_shuf"):
            user = st.radio(
                "Choose:",
                options=item["choices_shuf"],
                key=f"ans-{i}",
                horizontal=True,
                index=None  # start with nothing selected
            )
            st.session_state["quiz_answers"][i] = user or ""
        else:
            # Fill-in-the-blank
            user = st.text_input("Your answer", key=f"ans-{i}")
            st.session_state["quiz_answers"][i] = (user or "").strip()

        st.markdown("</div>", unsafe_allow_html=True)

    # Actions (submit / download / reset)
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        submit = st.button("Submit All ✅")
    with c2:
        dl_payload = {"meta": meta, "items": items}
        st.download_button("Download .json", data=json.dumps(dl_payload, indent=2), file_name="quiz.json")
    with c3:
        if st.button("Retake / Regenerate 🔁"):
            # Keep the same parameters; reshuffle choices
            for it in items:
                if it.get("choices"):
                    shuf, _ = shuffle_choices(it["choices"], it["answer"])
                    it["choices_shuf"] = shuf
            reset_attempt_state()
            # new start time for the retake
            st.session_state["quiz_started_at"] = datetime.now().isoformat()

    # ---------- Grade & Review ----------
    if submit and not st.session_state.get("quiz_submitted"):
        answers = st.session_state.get("quiz_answers", {})
        correct = 0
        review = []
        for i, it in enumerate(items, 1):
            gold = str(it.get("answer", ""))
            pred = str(answers.get(i, "") or "")
            is_mcq = bool(it.get("choices"))
            if is_mcq:
                ok = (pred == gold)
            else:
                ok = pred.strip().lower() == gold.strip().lower()
            correct += int(ok)
            review.append({
                "i": i,
                "q": it.get("q", ""),
                "your": pred or "—",
                "answer": gold,
                "ok": ok,
                "explanation": it.get("explanation", ""),
            })

        st.session_state["quiz_submitted"] = True
        st.session_state["quiz_score"] = {"correct": correct, "total": len(items), "review": review}

        # Persist attempt locally
        started_at_iso = st.session_state.get("quiz_started_at") or datetime.now().isoformat()
        submitted_at_iso = datetime.now().isoformat()
        attempt_id = save_quiz_attempt(
            snapshot_id=st.session_state.get("quiz_snapshot_id"),
            meta=meta,
            review=review,
            started_at=started_at_iso,
            submitted_at=submitted_at_iso,
        )
        st.session_state["quiz_attempt_id"] = attempt_id
        st.caption(f"Attempt saved · id: `{attempt_id[:8]}…`")

    # Show results if submitted
    if st.session_state.get("quiz_submitted"):
        sc = st.session_state["quiz_score"]
        pct = 100.0 * sc["correct"] / max(1, sc["total"])
        st.success(f"Score: **{sc['correct']} / {sc['total']}**  ({pct:.0f}%)")

        with st.expander("Review answers"):
            for r in sc["review"]:
                icon = "✅" if r["ok"] else "❌"
                st.markdown(f"**{r['i']}.** {icon} {r['q']}")
                st.caption(f"Your answer: {r['your'] or '—'}")
                if not r["ok"]:
                    st.write(f"**Correct:** {r['answer']}")
                if r.get("explanation"):
                    st.info(r["explanation"])

        # Past attempts (for this lecture)
# Past attempts (for this lecture) — with full Q/A details (no nested expanders)
st.markdown("### Past attempts")
past = load_attempts(lecture=meta.get("lecture"))
if not past:
    st.caption("No attempts saved yet.")
else:
    for a in past[:10]:
        when = (a.get("submitted_at") or a.get("saved_at") or "")[:16]
        title = (
            f"{when} · {a.get('lecture','Notes')} · "
            f"{a.get('type','MCQ')} · {a.get('difficulty','Auto')} · "
            f"Score: {a['score_raw']}/{a['score_max']} ({a['score_pct']}%) · "
            f"id: {a['attempt_id'][:8]}…"
        )

        with st.expander(title):
            # Type-safe access to snapshot_id (silences Pylance)
            snapshot_id = a.get("snapshot_id")
            snap = load_snapshot(snapshot_id) if isinstance(snapshot_id, str) else None
            snap_items = snap.get("items", []) if snap else []

            # Per-question review
            for r in a.get("items", []):
                idx = int(r.get("i", 0))
                q_text = r.get("q", "")
                your = r.get("your", "—")
                gold = r.get("answer", "")
                ok = bool(r.get("ok"))
                expl = r.get("explanation")

                st.markdown("---")
                st.markdown(f"**Q{idx}.** {q_text}")
                st.write(("✅ **Correct**" if ok else "❌ **Incorrect**") + f" — Your answer: `{your}`")
                if not ok:
                    st.write(f"**Correct:** `{gold}`")
                if expl:
                    st.caption(f"Explanation: {expl}")

                # If we have the snapshot, show original choices (if MCQ)
                try:
                    snap_item = snap_items[idx - 1] if idx - 1 >= 0 else None
                except Exception:
                    snap_item = None
                if snap_item and snap_item.get("choices_shuf"):
                    st.caption("Choices from original quiz:")
                    st.write(" · ".join(f"`{c}`" for c in snap_item["choices_shuf"]))

# ---------- Notes ----------
# Backend contract: POST /quiz
# Request: {
#   n, type: "mcq"|"fib"|"mix", difficulty, topic?,
#   section_ids?: string[], context?: string, corpus_id?: string, lecture_title?: string
# }
# Response: [ { q, choices?:[], answer, explanation? }, ... ]

st.markdown('</div>', unsafe_allow_html=True)
