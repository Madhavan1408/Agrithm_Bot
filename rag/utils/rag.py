"""
utils/rag.py
────────────
RAG pipeline for Agrithm.
LLM Backend: Ollama (local) — dhenu2-farming:latest
"""

import os
import sys
import logging
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agrithm_config import (
    EMBED_MODEL, VECTOR_STORE_PATH,
    TOP_K, MIN_SIMILARITY,
    OLLAMA_URL,
)

log = logging.getLogger(__name__)

OLLAMA_MODEL = "dhenu2-farming:latest"   # ← hardcoded model

# ── Loaded once at startup ────────────────────────────────────────
_embeddings = None
_db         = None


def _init():
    """Lazy-load embedding model and FAISS index."""
    global _embeddings, _db

    if _db is not None:
        return

    log.info("[RAG] Loading embedding model: %s", EMBED_MODEL)
    from langchain_huggingface import HuggingFaceEmbeddings
    _embeddings = HuggingFaceEmbeddings(
        model_name=EMBED_MODEL,
        encode_kwargs={"normalize_embeddings": True, "batch_size": 32}
    )

    log.info("[RAG] Loading FAISS index from: %s", VECTOR_STORE_PATH)
    from langchain_community.vectorstores import FAISS
    _db = FAISS.load_local(
        VECTOR_STORE_PATH, _embeddings,
        allow_dangerous_deserialization=True
    )

    log.info("[RAG] Using Ollama backend: %s @ %s", OLLAMA_MODEL, OLLAMA_URL)
    log.info("[RAG] Ready.")


# ── System Prompt ─────────────────────────────────────────────────
SYSTEM_PROMPT = """You are Agrithm, a trusted agricultural assistant for Indian farmers.
You specialize in Tamil Nadu farming — paddy, sugarcane, banana, vegetables, government schemes.

Rules:
1. Answer ONLY from the context provided. Never use outside knowledge.
2. If context doesn't cover the question, respond: "I don't have specific information on this. Please contact your local Krishi Vigyan Kendra."
3. Keep answers simple and short. Farmers may have low literacy.
4. Always cite your source: "According to TNAU advisory..." or "As per Vikaspedia..."
5. Never give chemical dosage without citing a source.
6. Respond in English — the calling code handles translation to farmer's language.
"""


# ── Ollama Backend ────────────────────────────────────────────────

def _call_ollama(user_msg: str) -> str:
    """Call local Ollama API with dhenu2-farming:latest."""
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_msg},
                ],
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "num_predict": 400,
                }
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()
    except requests.exceptions.ConnectionError:
        log.error("Ollama not running. Start it with: ollama serve")
        raise RuntimeError("Ollama server is not running at %s" % OLLAMA_URL)
    except requests.exceptions.Timeout:
        log.error("Ollama timed out — model may be too slow")
        raise RuntimeError("Ollama request timed out")
    except Exception as e:
        log.error("Ollama call failed: %s", e)
        raise


# ── Main RAG Function ─────────────────────────────────────────────

def query_agrithm(english_query: str) -> dict:
    """
    Full RAG pipeline.
    Takes English query → retrieves context → calls Ollama → returns answer.
    """
    _init()

    results = _db.similarity_search_with_score(english_query, k=TOP_K)

    relevant = []
    sources  = []
    for doc, score in results:
        sim = 1 - (score / 2)
        if sim >= MIN_SIMILARITY:
            relevant.append(doc)
            src = doc.metadata.get("source_file", "knowledge base")
            if src not in sources:
                sources.append(src)

    if not relevant:
        log.info("No relevant chunks found for: %s", english_query[:80])
        return {
            "answer":      "I don't have specific information on this topic. Please contact your local Krishi Vigyan Kendra for expert advice.",
            "sources":     [],
            "chunks_used": 0,
            "fallback":    True,
        }

    context = "\n\n".join(
        f"[Source: {doc.metadata.get('source_file', 'unknown')} | "
        f"Category: {doc.metadata.get('category', 'general')}]\n"
        f"{doc.page_content.strip()}"
        for doc in relevant
    )

    user_msg = (
        f"Context:\n{context}\n\n"
        f"---\n"
        f"Farmer's question: {english_query}\n\n"
        f"Answer using ONLY the context above."
    )

    try:
        answer = _call_ollama(user_msg)
        log.info("Ollama answered using %d chunks", len(relevant))
    except Exception as e:
        log.error("Ollama call failed: %s", e)
        return {
            "answer":      "Sorry, I am unable to answer right now. Please try again later.",
            "sources":     [],
            "chunks_used": 0,
            "fallback":    True,
        }

    return {
        "answer":      answer,
        "sources":     sources,
        "chunks_used": len(relevant),
        "fallback":    False,
    }


def generate_daily_digest(district: str, crop: str) -> str:
    """Generate a farmer-personalized daily digest using RAG."""
    query = (
        f"Latest agricultural advisories, weather alerts, pest warnings, "
        f"and government schemes for {crop} farmers in {district} district Tamil Nadu"
    )
    result = query_agrithm(query)
    return result["answer"]