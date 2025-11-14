# app/routers/chat.py
from __future__ import annotations

import os
from typing import List, Dict, Any, Optional, Sequence, Union, cast

from fastapi import APIRouter, HTTPException

from app.models.schemas import ChatRequest, ChatResponse, ChatMessage
from app.services.vector import search as vector_search

# ----------------------------
# Optional: OpenAI client
# ----------------------------
try:
    from openai import OpenAI

    _openai: Optional[OpenAI] = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception:
    _openai = None

router = APIRouter()


# ----------------------------
# System prompt (governs answer style)
# ----------------------------
SYSTEM_PROMPT = """
You are Enginuity AI — a lecture-grounded teaching assistant.
Use ONLY the information provided in the CONTEXT FROM NOTES.

When answering:
- If the context clearly or partially answers the question, say what the notes DO tell us.
- If an aspect of the question is missing (e.g., the question asks "when" but the notes only say WHAT happened), then answer like:
  "The notes mention that you did X, but they do not specify when."
- Only use the exact sentence "I could not find this information in the lecture notes." when there is no clearly relevant information at all.

Always be concise, factual, and avoid adding outside information that is not in the context.
""".strip()


# ============================================================
# Helpers
# ============================================================
MsgLike = Union[ChatMessage, Dict[str, Any]]


def _msg_to_plain_dict(msg: MsgLike) -> Dict[str, Any]:
    """Convert ChatMessage or dict to a plain Python dict."""
    if isinstance(msg, ChatMessage):
        # pydantic v2
        return msg.model_dump()
    if hasattr(msg, "dict"):
        return msg.dict()  # type: ignore
    return dict(msg)


def _last_user_message(messages: Sequence[MsgLike]) -> str:
    """Extract the most recent user message."""
    for msg in reversed(messages):
        m = _msg_to_plain_dict(msg)
        if m.get("role") == "user":
            content = m.get("content", "")
            if isinstance(content, dict):
                return str(content.get("text", ""))
            return str(content)
    # fallback if weird
    return ""


def _build_context_block(hits: List[Dict[str, Any]]) -> str:
    """Construct a text block out of vector search hits."""
    if not hits:
        return ""

    parts: List[str] = []
    for idx, h in enumerate(hits, 1):
        sec = h.get("section_id", f"match-{idx}")
        source = h.get("source", "Notes")
        score = h.get("score")

        header = f"[{sec} | {source}"
        if score is not None:
            header += f" | score={score:.2f}"
        header += "]"

        snippet = h.get("document") or h.get("snippet") or ""
        parts.append(f"{header}\n{snippet}\n")

    return "\n\n".join(parts)


def _llm_answer(
    question: str,
    context_block: str,
    history: Sequence[MsgLike],
    temperature: float = 0.2,
) -> str:
    """Send the constructed prompt to OpenAI, or fall back if not configured."""
    # If no OpenAI configured → fallback
    if not _openai:
        if not context_block:
            return "I could not find any relevant information in the lecture notes."
        return (
            "Model access is not configured. But based on your notes:\n\n"
            f"{context_block}"
        )

    # Normalize last 6–8 messages from history
    trimmed_messages: List[Dict[str, str]] = []
    for msg in history[-8:]:
        m = _msg_to_plain_dict(msg)
        role = str(m.get("role", "user"))
        content: Any = m.get("content", "")
        if isinstance(content, dict):
            content = content.get("text", "")
        trimmed_messages.append({"role": role, "content": str(content)})

    # Build full prompt
    messages_payload: List[Dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"CONTEXT FROM NOTES:\n\n{context_block}"},
    ] + trimmed_messages

    # Explicit user query to focus the model
    messages_payload.append(
        {
            "role": "user",
            "content": (
                "Using ONLY the lecture context above, answer this question:\n\n"
                f"{question}"
            ),
        }
    )

    # Pylance / typing: cast to the expected type from OpenAI SDK
    from openai.types.chat import ChatCompletionMessageParam

    typed_messages = cast(List[ChatCompletionMessageParam], messages_payload)

    resp = _openai.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=float(temperature),
        messages=typed_messages,
    )
    return (resp.choices[0].message.content or "").strip()


# ============================================================
# Main Chat Endpoint
# ============================================================
@router.post("", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    if not req.messages:
        raise HTTPException(status_code=400, detail="No messages provided.")

    # 1) Latest question
    question = _last_user_message(req.messages)
    if not question.strip():
        raise HTTPException(status_code=400, detail="Empty question.")

    # 2) Retrieve context from vector DB
    try:
        top_k = max(1, min(int(req.top_k or 5), 15))
    except Exception:
        top_k = 5

    hits = vector_search(question, top_k=top_k)
    context_block = _build_context_block(hits)

    # 3) LLM answer
    answer_text = _llm_answer(
        question=question,
        context_block=context_block,
        history=req.messages,
        temperature=float(req.temperature or 0.2),
    )

    return ChatResponse(
        text=answer_text,
        citations=hits,  # send back the vector hits
    )
