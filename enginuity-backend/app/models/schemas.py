# app/models/schemas.py
from typing import List, Any, Dict, Optional
from pydantic import BaseModel

class SearchHit(BaseModel):
    title: str
    snippet: str | None = None
    score: float | None = None
    section_id: str | None = None
    source: str | None = None

class SearchRequest(BaseModel):
    q: str
    top_k: int = 5
    mode: str = "hybrid"  # hybrid|keyword|semantic

class QuizItem(BaseModel):
    q: str
    choices: List[str] = []
    answer: str
    explanation: str | None = None

class QuizRequest(BaseModel):
    n: int = 6
    type: str = "mcq"   # mcq|fib|mix
    difficulty: str = "auto"
    topic: str | None = None

class NotesDoc(BaseModel):
    lecture_title: str = "Notes"
    generated_at: int | None = None
    sections: list = []

class ExportRequest(BaseModel):
    format: str = "pdf"  # pdf|docx|anki|md


class ChatMessage(BaseModel):
    role: str  # "user", "assistant", "system"
    content: Any  # you can keep this as str if you prefer


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    top_k: Optional[int] = 5
    temperature: Optional[float] = 0.2


class ChatResponse(BaseModel):
    text: str
    citations: List[Dict[str, Any]] = []
