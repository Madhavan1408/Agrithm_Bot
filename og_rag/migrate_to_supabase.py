# migrate_to_supabase.py
"""
One-time migration: Load existing FAISS index → push all chunks to Supabase pgvector.
Run from project root:
    python migrate_to_supabase.py
"""

import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agrithm_config import EMBED_MODEL, VECTOR_STORE_PATH
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from supabase import create_client, Client

SUPABASE_URL = "https://ohkyeoqjrlwmtapsfrtb.supabase.co" 
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9oa3llb3Fqcmx3bXRhcHNmcnRiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzUxMjA2MDksImV4cCI6MjA5MDY5NjYwOX0.eBq9nMTcvL7PSFhZ0pifvSSmJwQQcln3cZi0yZu7kxk"

def migrate():
    print("[Migration] Loading embedding model...")
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBED_MODEL,
        encode_kwargs={"normalize_embeddings": True, "batch_size": 32},
    )

    print("[Migration] Loading FAISS index...")
    db = FAISS.load_local(
        VECTOR_STORE_PATH, embeddings,
        allow_dangerous_deserialization=True
    )

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # FAISS internal docstore holds all documents
    docs = list(db.docstore._dict.values())
    print(f"[Migration] Found {len(docs)} chunks to migrate...")

    batch = []
    BATCH_SIZE = 100

    for i, doc in enumerate(docs):
        # Re-embed each chunk (or extract from FAISS index directly)
        vec = embeddings.embed_query(doc.page_content)
        batch.append({
            "content":     doc.page_content.strip(),
            "source_file": doc.metadata.get("source_file", "unknown"),
            "category":    doc.metadata.get("category", "general"),
            "language":    doc.metadata.get("language", "en"),
            "embedding":   vec,  # list of floats
        })

        if len(batch) >= BATCH_SIZE:
            supabase.table("agrithm_chunks").insert(batch).execute()
            print(f"  Inserted batch up to chunk {i+1}")
            batch = []

    if batch:
        supabase.table("agrithm_chunks").insert(batch).execute()
        print(f"  Inserted final batch of {len(batch)} chunks")

    print("[Migration] DONE. All chunks are in Supabase.")

if __name__ == "__main__":
    migrate()