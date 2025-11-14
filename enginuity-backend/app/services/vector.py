# app/services/vector.py
from typing import List, Dict
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction  # type: ignore
from chromadb.api import ClientAPI
from app.core.config import get_settings

# Use a small local embedding model (no API key required)
_embedder = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")


def _client() -> ClientAPI:
    settings = get_settings()
    persist = Path(settings.VECTORDB_DIR).resolve()
    persist.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(persist))


def collection(
    name: str = "enginuity",
) -> chromadb.api.models.Collection.Collection:  # type: ignore[attr-defined]
    cli = _client()
    try:
        return cli.get_collection(name=name, embedding_function=_embedder)
    except Exception:
        return cli.create_collection(name=name, embedding_function=_embedder)


def index_sections(lecture_title: str, sections: List[Dict]) -> None:
    """
    Index lecture sections into Chroma.
    Each section dict is expected to have:
    - "id": stable section id (e.g., "sec-1")
    - "content": text content
    """
    col = collection()
    ids = [s["id"] for s in sections]
    docs = [s["content"] for s in sections]
    metas = [{"title": lecture_title, "section_id": s["id"]} for s in sections]

    col.upsert(ids=ids, documents=docs, metadatas=metas)


def search(q: str, top_k: int = 5) -> List[Dict]:
    """
    Semantic search over indexed sections.

    Returns a list of dicts:
    {
        "title": str,        # human label (e.g., "Match")
        "snippet": str,      # short preview
        "document": str,     # full text for LLM context
        "score": float | None,
        "section_id": str | None,
        "source": str | None,  # lecture title
    }
    """
    col = collection()
    res = col.query(query_texts=[q], n_results=top_k)

    out: List[Dict] = []
    if not res or not res.get("documents"):
        return out

    docs = res["documents"][0]
    metas = res["metadatas"][0]
    dists = res.get("distances", [[]])[0] if res.get("distances") else [None] * len(docs)

    for doc, meta, dist in zip(docs, metas, dists):
        snippet = doc[:280] + ("…" if len(doc) > 280 else "")
        out.append(
            {
                "title": "Match",
                "snippet": snippet,
                "document": doc,
                "score": 1.0 - float(dist) if dist is not None else None,  # convert distance to pseudo-score
                "section_id": meta.get("section_id"),
                "source": meta.get("title", "Notes"),
            }
        )

    return out
