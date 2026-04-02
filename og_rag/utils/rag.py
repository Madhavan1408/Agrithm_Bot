"""
utils/rag.py
────────────
RAG pipeline for Agrithm — Supabase pgvector backend.

Architecture:
  User query (any language, already translated to EN by bot.py)
      │
      ▼
  Embed query  ──→  HuggingFaceEmbeddings (LaBSE)
      │
      ▼
  Supabase RPC: match_agrithm_chunks()
      │  (cosine similarity search via pgvector)
      ▼
  Top-K relevant chunks retrieved
      │
      ▼
  Assemble prompt: [SYSTEM] + [Context chunks] + [Farmer question]
      │
      ▼
  Ollama API  (OLLAMA_URL / OLLAMA_MODEL from agrithm_config)
      │
      ▼
  Structured response dict  →  bot.py
"""

import os
import sys
import logging
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agrithm_config import (
    EMBED_MODEL,
    TOP_K,
    MIN_SIMILARITY,
    OLLAMA_URL,
    OLLAMA_MODEL,
)

log = logging.getLogger(__name__)

# ── Supabase credentials (set in environment or .env) ─────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY")  # anon key is fine for SELECT

# ── Lazy-loaded embedding model ───────────────────────────────────
_embeddings  = None
_init_failed = False


def _init() -> bool:
    """
    Lazy-load the embedding model only.
    Supabase is stateless HTTP — no persistent connection needed.
    """
    global _embeddings, _init_failed

    if _embeddings is not None:
        return True
    if _init_failed:
        return False

    if not SUPABASE_URL or not SUPABASE_KEY:
        log.error(
            "[RAG] SUPABASE_URL or SUPABASE_ANON_KEY not set in environment. "
            "RAG disabled."
        )
        _init_failed = True
        return False

    try:
        log.info("[RAG] Loading embedding model: %s", EMBED_MODEL)
        from langchain_huggingface import HuggingFaceEmbeddings
        _embeddings = HuggingFaceEmbeddings(
            model_name=EMBED_MODEL,
            encode_kwargs={"normalize_embeddings": True, "batch_size": 32},
        )
        log.info("[RAG] Embedding model ready. Supabase backend: %s", SUPABASE_URL)
        return True

    except Exception as e:
        log.error("[RAG] Embedding model init failed: %s", e)
        _init_failed = True
        return False


# ── Supabase vector search ────────────────────────────────────────
def _search_supabase(query_vector: list[float]) -> list[dict]:
    """
    Call Supabase RPC 'match_agrithm_chunks' to retrieve similar chunks.

    Returns list of dicts:
        { content, source_file, category, similarity }
    """
    try:
        resp = requests.post(
            f"{SUPABASE_URL}/rest/v1/rpc/match_agrithm_chunks",
            headers={
                "apikey":        SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type":  "application/json",
            },
            json={
                "query_embedding": query_vector,
                "match_threshold": MIN_SIMILARITY,
                "match_count":     TOP_K,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()  # list of row dicts

    except requests.exceptions.ConnectionError:
        log.error("[RAG] Cannot reach Supabase at %s", SUPABASE_URL)
        raise RuntimeError("Supabase is unreachable")

    except requests.exceptions.Timeout:
        log.error("[RAG] Supabase RPC timed out")
        raise RuntimeError("Supabase similarity search timed out")

    except requests.exceptions.HTTPError as e:
        log.error("[RAG] Supabase HTTP error: %s — %s", e, resp.text)
        raise


# ── System Prompt ─────────────────────────────────────────────────
SYSTEM_PROMPT = (
    "You are Agrithm, a trusted agricultural assistant for Indian farmers.\n"
    "You specialize in Tamil Nadu farming — paddy, sugarcane, banana, vegetables, "
    "government schemes.\n\n"
    "Rules:\n"
    "1. Answer ONLY from the context provided. Never use outside knowledge.\n"
    "2. If context doesn't cover the question, respond: "
    "'I don't have specific information on this. "
    "Please contact your local Krishi Vigyan Kendra.'\n"
    "3. Keep answers simple and short. Farmers may have low literacy.\n"
    "4. Always cite your source: 'According to TNAU advisory...' "
    "or 'As per Vikaspedia...'\n"
    "5. Never give chemical dosage without citing a source.\n"
    "6. Respond in English — the calling code handles translation to "
    "farmer's language.\n"
)


# ── Ollama backend ────────────────────────────────────────────────
def _call_ollama(user_msg: str) -> str:
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
                },
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()

    except requests.exceptions.ConnectionError:
        log.error("[RAG] Ollama not reachable at %s", OLLAMA_URL)
        raise RuntimeError(f"Ollama server is not running at {OLLAMA_URL}")

    except requests.exceptions.Timeout:
        log.error("[RAG] Ollama timed out")
        raise RuntimeError("Ollama request timed out")

    except Exception as e:
        log.error("[RAG] Ollama call failed: %s", e)
        raise


# ── Main RAG function ─────────────────────────────────────────────
def query_agrithm(english_query: str) -> dict:
    """
    Full RAG pipeline — Supabase edition.

    Flow:
      1. Embed the query  (HuggingFace LaBSE)
      2. Search Supabase  (pgvector cosine similarity via RPC)
      3. Build prompt     (system + context chunks + question)
      4. Call Ollama      (llm answer)
      5. Return structured response

    Returns:
        {
          "answer":      str,
          "sources":     list[str],
          "chunks_used": int,
          "fallback":    bool,
        }
    """
    _FALLBACK = lambda msg: {
        "answer":      msg,
        "sources":     [],
        "chunks_used": 0,
        "fallback":    True,
    }

    # ── 1. Init embedding model ───────────────────────────────────
    if not _init():
        return _FALLBACK(
            "I don't have specific information on this topic. "
            "Please contact your local Krishi Vigyan Kendra for expert advice."
        )

    # ── 2. Embed the query ────────────────────────────────────────
    try:
        query_vector = _embeddings.embed_query(english_query)
    except Exception as e:
        log.error("[RAG] Embedding failed: %s", e)
        return _FALLBACK(
            "Sorry, I am unable to process your question right now. "
            "Please try again later."
        )

    # ── 3. Search Supabase ────────────────────────────────────────
    try:
        rows = _search_supabase(query_vector)
    except Exception as e:
        log.error("[RAG] Supabase search failed: %s", e)
        return _FALLBACK(
            "Sorry, I am unable to answer right now. Please try again later."
        )

    if not rows:
        log.info("[RAG] No relevant chunks for: %.80s", english_query)
        return _FALLBACK(
            "I don't have specific information on this topic. "
            "Please contact your local Krishi Vigyan Kendra for expert advice."
        )

    # ── 4. Build context prompt ───────────────────────────────────
    sources = []
    context_parts = []

    for row in rows:
        src = row.get("source_file") or "knowledge base"
        if src not in sources:
            sources.append(src)
        context_parts.append(
            f"[Source: {src} | Category: {row.get('category', 'general')}]\n"
            f"{row['content'].strip()}"
        )

    context = "\n\n".join(context_parts)
    user_msg = (
        f"Context:\n{context}\n\n"
        f"---\n"
        f"Farmer's question: {english_query}\n\n"
        f"Answer using ONLY the context above."
    )

    # ── 5. Call Ollama ────────────────────────────────────────────
    try:
        answer = _call_ollama(user_msg)
        log.info(
            "[RAG] Answered using %d chunks from: %s",
            len(rows), sources,
        )
    except Exception as e:
        log.error("[RAG] Ollama call failed: %s", e)
        return _FALLBACK(
            "Sorry, I am unable to answer right now. Please try again later."
        )

    return {
        "answer":      answer,
        "sources":     sources,
        "chunks_used": len(rows),
        "fallback":    False,
    }


# ── Daily digest (unchanged interface) ───────────────────────────
def generate_daily_digest(district: str, crop: str) -> str:
    query = (
        f"Latest agricultural advisories, weather alerts, pest warnings, "
        f"and government schemes for {crop} farmers in {district} district Tamil Nadu"
    )
    result = query_agrithm(query)
    return result["answer"]