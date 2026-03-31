import os
import hashlib
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_huggingface import HuggingFaceEmbeddings          # ✅ updated import
from langchain_community.vectorstores import FAISS

# 1. Load
loader = DirectoryLoader(
    path=r"D:\agribot\rag_data_llm",
    glob="**/*.txt",
    loader_cls=lambda path: TextLoader(path, encoding='utf-8', autodetect_encoding=True)
)
documents = loader.load()

# 2. Inject metadata
for doc in documents:
    fname = os.path.basename(doc.metadata.get('source', ''))
    doc.metadata['source_file'] = fname
    parts = fname.replace('.txt', '').split('_')
    doc.metadata['category'] = parts[1] if len(parts) > 1 else 'general'

# 3. Chunk
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    add_start_index=True
)
chunks = splitter.split_documents(documents)

# 4. Deduplicate
seen = set()
unique_chunks = []
for chunk in chunks:
    h = hashlib.md5(chunk.page_content.strip().encode()).hexdigest()
    if h not in seen:
        seen.add(h)
        unique_chunks.append(chunk)

print(f"Total chunks: {len(chunks)} → After dedup: {len(unique_chunks)}")

# 5. Install updated package first:
#    pip install -U langchain-huggingface
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    model_kwargs={'device': 'cpu'},
    encode_kwargs={
        'normalize_embeddings': True,
        'batch_size': 32,           # ✅ lowered to 32 to avoid memory errors on CPU
    }
)

# 6. Warm-up test before full run
print("Testing model with a sample...")
test = embeddings.embed_query("test sentence")
print(f"Embedding dim: {len(test)} ✅")  # should print 384

# 7. FAISS batched indexing
BATCH_SIZE = 300  # ✅ reduced from 500 to be safer on memory
print(f"Embedding {len(unique_chunks)} chunks in batches of {BATCH_SIZE}...")

db = None
total_batches = -(-len(unique_chunks) // BATCH_SIZE)  # ceiling division

for i in range(0, len(unique_chunks), BATCH_SIZE):
    batch = unique_chunks[i : i + BATCH_SIZE]
    batch_num = i // BATCH_SIZE + 1
    print(f"  Batch {batch_num} / {total_batches} ({len(batch)} chunks)")
    try:
        if db is None:
            db = FAISS.from_documents(batch, embeddings)
        else:
            db.add_documents(batch)
    except Exception as e:
        print(f"  ❌ Error in batch {batch_num}: {e}")
        raise

db.save_local("vector_store")
print("✅ Vector store saved.")
