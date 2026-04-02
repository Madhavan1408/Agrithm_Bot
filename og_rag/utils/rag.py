"""
utils/rag.py
────────────
RAG pipeline for Agrithm.
LLM Backend: Ollama — dhenu2-farming:latest

FIXES applied:
  FIX A: _init_failed flag — stops retrying after FAISS/NumPy ABI mismatch.
          To fix the environment:
            pip uninstall faiss-cpu numpy -y
            pip install "numpy<2"
            pip install faiss-cpu
  FIX B: OLLAMA_URL imported from agrithm_config — same URL as bot.py.
          No more hardcoded or conflicting endpoints.
"""

import os
import sys
import logging
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agrithm_config import (
    EMBED_MODEL,
    VECTOR_STORE_PATH,
    TOP_K,
    MIN_SIMILARITY,
    OLLAMA_URL,        # FIX B: single source of truth from config
    OLLAMA_MODEL,      # FIX B: also from config now
)

log = logging.getLogger(__name__)

# ── Loaded once at startup ────────────────────────────────────────
_embeddings  = None
_db          = None
_init_failed = False   # FIX A: set True on hard failure, prevents infinite retry


def _init() -> bool:
    """
    Lazy-load embedding model and FAISS index.
    Returns True on success, False if init failed (permanently).

    FIX A: On AttributeError (NumPy 2.x / FAISS 1.x ABI mismatch) or any
           other exception, sets _init_failed=True so subsequent calls return
           immediately without re-running the same failing code path.
    """
    global _embeddings, _db, _init_failed

    if _db is not None:
        return True

    # FIX A: bail early — don't retry a known-broken environment
    if _init_failed:
        return False

    try:
        if not os.path.exists(VECTOR_STORE_PATH):
            log.warning(
                "[RAG] Vector store not found at '%s' — RAG disabled. "
                "Run your ingest script to build it.",
                VECTOR_STORE_PATH,
            )
            _init_failed = True
            return False

        log.info("[RAG] Loading embedding model: %s", EMBED_MODEL)
        from langchain_huggingface import HuggingFaceEmbeddings
        _embeddings = HuggingFaceEmbeddings(
            model_name=EMBED_MODEL,
            encode_kwargs={"normalize_embeddings": True, "batch_size": 32},
        )

        log.info("[RAG] Loading FAISS index from: %s", VECTOR_STORE_PATH)
        from langchain_community.vectorstores import FAISS
        _db = FAISS.load_local(
            VECTOR_STORE_PATH, _embeddings,
            allow_dangerous_deserialization=True,
        )

        log.info("[RAG] Using Ollama backend: %s @ %s", OLLAMA_MODEL, OLLAMA_URL)
        log.info("[RAG] Ready.")
        return True

    except AttributeError as e:
        # NumPy 2.x / FAISS 1.x ABI mismatch — _ARRAY_API not found
        log.error(
            "[RAG] FAISS cannot load due to NumPy ABI mismatch.\n"
            "  Fix with:\n"
            "    pip uninstall faiss-cpu numpy -y\n"
            "    pip install \"numpy<2\"\n"
            "    pip install faiss-cpu\n"
            "  Then restart the bot.\n"
            "  Raw error: %s", e,
        )
        _init_failed = True
        return False

    except Exception as e:
        log.error("[RAG] Init failed: %s", e)
        _init_failed = True
        return False


# ── System Prompt ─────────────────────────────────────────────────
SYSTEM_PROMPT = (
    "You are Agrithm, a trusted agricultural assistant for Indian farmers.\n"
    "You specialize in Tamil Nadu farming — paddy, sugarcane, banana, vegetables, government schemes.\n\n"
    "Rules:\n"
    "1. Answer ONLY from the context provided. Never use outside knowledge.\n"
    "2. If context doesn't cover the question, respond: "
    "'I don't have specific information on this. Please contact your local Krishi Vigyan Kendra.'\n"
    "3. Keep answers simple and short. Farmers may have low literacy.\n"
    "4. Always cite your source: 'According to TNAU advisory...' or 'As per Vikaspedia...'\n"
    "5. Never give chemical dosage without citing a source.\n"
    "6. Respond in English — the calling code handles translation to farmer's language.\n"
)


# ── Ollama Backend ────────────────────────────────────────────────
def _call_ollama(user_msg: str) -> str:
    """
    Call Ollama API.
    FIX B: Uses OLLAMA_URL from agrithm_config — same as bot.py.
    """
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/chat",   # FIX B: from config, not hardcoded
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
                },
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()

    except requests.exceptions.ConnectionError:
        log.error("[RAG] Ollama not reachable at %s — is ollama serve running?", OLLAMA_URL)
        raise RuntimeError(f"Ollama server is not running at {OLLAMA_URL}")

    except requests.exceptions.Timeout:
        log.error("[RAG] Ollama timed out — model may still be loading")
        raise RuntimeError("Ollama request timed out")

    except Exception as e:
        log.error("[RAG] Ollama call failed: %s", e)
        raise


# ── Main RAG Function ─────────────────────────────────────────────
def query_agrithm(english_query: str) -> dict:
    """
    Full RAG pipeline.
    Takes an English query → retrieves context chunks → calls Ollama → returns answer.

    Returns a dict:
      answer      : str   — the answer text (never None)
      sources     : list  — source filenames used
      chunks_used : int   — number of relevant chunks found
      fallback    : bool  — True if RAG could not answer (no chunks / init failed)
    """
    if not _init():
        return {
            "answer":      (
                "I don't have specific information on this topic. "
                "Please contact your local Krishi Vigyan Kendra for expert advice."
            ),
            "sources":     [],
            "chunks_used": 0,
            "fallback":    True,
        }

    results  = _db.similarity_search_with_score(english_query, k=TOP_K)
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
        log.info("[RAG] No relevant chunks found for: %.80s", english_query)
        return {
            "answer": (
                "I don't have specific information on this topic. "
                "Please contact your local Krishi Vigyan Kendra for expert advice."
            ),
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
        log.info("[RAG] Answered using %d chunks from: %s", len(relevant), sources)
    except Exception as e:
        log.error("[RAG] Ollama call failed: %s", e)
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
    """Generate a farmer-personalised daily digest using RAG."""
    query = (
        f"Latest agricultural advisories, weather alerts, pest warnings, "
        f"and government schemes for {crop} farmers in {district} district Tamil Nadu"
    )
    result = query_agrithm(query)
    return result["answer"]