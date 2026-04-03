"""
utils/rag.py
────────────
RAG pipeline for Agrithm — Supabase pgvector backend.

Architecture:
  User query (English, translated by bot.py)
      │
      ▼
  Embed query  ──→  HuggingFaceEmbeddings (LaBSE, 768-dim)
      │
      ▼
  Supabase RPC: match_agrithm_chunks()
      │  (cosine similarity search via pgvector)
      ▼
  Top-K relevant chunks returned to bot.py
      │
      ▼
  bot.py builds full prompt:
      [Farmer Profile] + [Language Instruction] + [Chunks] + [Question]
      │
      ▼
  bot.py calls Ollama  (dhenu2-farming:latest)
      │
      ▼
  Response translated + sent to farmer

NOTE:
  This file does NOT call Ollama.
  It only embeds the query and fetches relevant chunks from Supabase.
  All LLM calls are handled by bot.py so farmer profile, language,
  and system prompt are applied correctly in one place.
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
)

log = logging.getLogger(__name__)

# ── Supabase credentials ──────────────────────────────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "").strip()

# ── Lazy-loaded embedding model ───────────────────────────────────
_embeddings  = None
_init_failed = False


def _init() -> bool:
    """
    Lazy-load the LaBSE embedding model on first call.
    Returns True if ready, False if failed.
    """
    global _embeddings, _init_failed

    if _embeddings is not None:
        return True
    if _init_failed:
        return False

    if not SUPABASE_URL or not SUPABASE_KEY:
        log.error(
            "[RAG] SUPABASE_URL or SUPABASE_ANON_KEY missing in .env — RAG disabled"
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
        log.info("[RAG] ✅ Embedding model ready | Supabase: %s", SUPABASE_URL)
        return True

    except ImportError:
        log.error(
            "[RAG] langchain_huggingface not installed. "
            "Run: pip install langchain-huggingface sentence-transformers"
        )
        _init_failed = True
        return False

    except Exception as exc:
        log.error("[RAG] Embedding model init failed: %s", exc)
        _init_failed = True
        return False


# ── Supabase pgvector search ──────────────────────────────────────
def _search_supabase(query_vector: list[float]) -> list[dict]:
    """
    Calls Supabase RPC 'match_agrithm_chunks' with the query embedding.

    Required SQL function in Supabase (run once in SQL Editor):

        CREATE OR REPLACE FUNCTION match_agrithm_chunks(
            query_embedding vector(768),
            match_threshold float,
            match_count     int
        )
        RETURNS TABLE (
            id          bigint,
            content     text,
            source_file text,
            category    text,
            similarity  float
        )
        LANGUAGE sql STABLE AS $$
            SELECT
                id,
                content,
                source_file,
                category,
                1 - (embedding <=> query_embedding) AS similarity
            FROM agrithm_chunks
            WHERE 1 - (embedding <=> query_embedding) > match_threshold
            ORDER BY embedding <=> query_embedding
            LIMIT match_count;
        $$;

    Returns list of dicts with keys: id, content, source_file, category, similarity
    Raises RuntimeError on connection/timeout failures.
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
        rows = resp.json()

        if not isinstance(rows, list):
            log.error("[RAG] Unexpected Supabase response: %s", rows)
            return []

        log.info(
            "[RAG] Supabase returned %d chunks (threshold=%.2f, top_k=%d)",
            len(rows), MIN_SIMILARITY, TOP_K,
        )
        return rows

    except requests.exceptions.ConnectionError:
        log.error("[RAG] Cannot reach Supabase at %s", SUPABASE_URL)
        raise RuntimeError("Supabase is unreachable")

    except requests.exceptions.Timeout:
        log.error("[RAG] Supabase RPC timed out after 15s")
        raise RuntimeError("Supabase similarity search timed out")

    except requests.exceptions.HTTPError as exc:
        log.error("[RAG] Supabase HTTP %s: %s", exc.response.status_code, resp.text[:200])
        raise


# ── Main RAG function (chunks only — NO Ollama call) ─────────────
def get_relevant_chunks(english_query: str) -> dict:
    """
    Embeds the English query and retrieves relevant chunks from Supabase.
    Does NOT call Ollama — that is handled entirely by bot.py.

    Args:
        english_query: Farmer's question already translated to English

    Returns:
        {
            "chunks":      list[{"topic": str, "content": str, "source": str}],
            "chunks_used": int,
            "context_str": str,   # pre-formatted string ready to inject into prompt
            "fallback":    bool,  # True = no chunks found or error occurred
            "error":       str | None,
        }

    The caller (bot.py disease_rag_answer) uses context_str directly in the prompt:
        prompt = f"{farmer_ctx}\\n{result['context_str']}\\nFarmer says: {description}"
    """

    _empty = lambda err=None: {
        "chunks":      [],
        "chunks_used": 0,
        "context_str": "",
        "fallback":    True,
        "error":       err,
    }

    # ── 1. Init embedding model ───────────────────────────────────
    if not _init():
        return _empty("Embedding model not available")

    # ── 2. Embed the query ────────────────────────────────────────
    try:
        log.info("[RAG] Embedding query: %s", english_query[:80])
        query_vector = _embeddings.embed_query(english_query)
    except Exception as exc:
        log.error("[RAG] Embedding failed: %s", exc)
        return _empty(f"Embedding failed: {exc}")

    # ── 3. Search Supabase pgvector ───────────────────────────────
    try:
        rows = _search_supabase(query_vector)
    except Exception as exc:
        log.error("[RAG] Supabase search error: %s", exc)
        return _empty(str(exc))

    if not rows:
        log.warning("[RAG] No relevant chunks found for: %s", english_query[:80])
        return _empty("No relevant chunks found")

    # ── 4. Format chunks for prompt injection ─────────────────────
    chunks     = []
    parts      = ["--- Relevant knowledge from Agrithm database ---"]

    for i, row in enumerate(rows, 1):
        content = (row.get("content") or "").strip()
        if not content:
            continue

        source   = row.get("source_file") or "knowledge base"
        category = row.get("category")    or "general"
        sim      = row.get("similarity",  0.0)

        chunks.append({
            "topic":   category,
            "content": content,
            "source":  source,
        })

        parts.append(
            f"[{i}] Category: {category} | Source: {source} "
            f"| Relevance: {sim:.2f}\n{content}"
        )

    parts.append("--- End of knowledge context ---")

    context_str = "\n\n".join(parts)

    log.info(
        "[RAG] ✅ Built context: %d chunks, %d chars | sources: %s",
        len(chunks),
        len(context_str),
        list({c["source"] for c in chunks}),
    )

    return {
        "chunks":      chunks,
        "chunks_used": len(chunks),
        "context_str": context_str,
        "fallback":    False,
        "error":       None,
    }


# ── Keep query_agrithm as alias so old imports don't break ────────
def query_agrithm(english_query: str) -> dict:
    """
    Backward-compatible wrapper around get_relevant_chunks().
    Returns same shape as before so any existing callers still work.
    """
    result = get_relevant_chunks(english_query)
    return {
        "answer":      result["context_str"],   # context string (not LLM answer)
        "sources":     [c["source"] for c in result["chunks"]],
        "chunks_used": result["chunks_used"],
        "fallback":    result["fallback"],
    }


# ── Daily digest helper (uses bot-level Ollama, not internal) ─────
def get_digest_chunks(district: str, crop: str) -> dict:
    """
    Fetches relevant chunks for the morning digest.
    bot.py calls this and builds the digest prompt with farmer context.
    """
    query = (
        f"Latest agricultural advisories, weather alerts, pest warnings, "
        f"and government schemes for {crop} farmers in {district} district India"
    )
    return get_relevant_chunks(query)