# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.routers import health, notes, search, quiz, chat, export, upload, corpus
import os
os.environ["CHROMA_TELEMETRY_ENABLED"] = "false"
os.environ["ANONYMIZED_TELEMETRY"] = "false"

# Load settings
settings = get_settings()

# Initialize FastAPI app
app = FastAPI(
    title="Enginuity Backend",
    version="0.1.0",
    description="Backend API for Enginuity AI"
)

# --- CORS Configuration ---
raw_origins = settings.CORS_ALLOW_ORIGINS
if isinstance(raw_origins, str):
    origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
elif isinstance(raw_origins, list):
    origins = [str(o).strip() for o in raw_origins if str(o).strip()]
else:
    origins = ["http://localhost:8501"]  # default fallback

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(notes.router, prefix="/notes", tags=["notes"])
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(quiz.router, prefix="/quiz", tags=["quiz"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(export.router, prefix="/export", tags=["export"])
app.include_router(upload.router, prefix="/upload", tags=["upload"])
app.include_router(corpus.router, prefix="/corpus", tags=["corpus"])

# --- Root Route ---
@app.get("/")
def root():
    return {
        "message": "Enginuity Backend is running ✅",
        "version": "0.1.0",
        "origins_allowed": origins,
    }
