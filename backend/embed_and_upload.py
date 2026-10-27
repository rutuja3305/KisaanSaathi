import os
import sqlite3
from dotenv import load_dotenv
from supabase import create_client
from sentence_transformers import SentenceTransformer


# =========================================================
# CONFIGURATION
# =========================================================

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

SQLITE_DB = r"knowledge\knowledge.sqlite"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_VERSION = "v1"

BATCH_SIZE = 50


# =========================================================
# VALIDATION
# =========================================================

if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL missing from .env")

if not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_KEY missing from .env")


# =========================================================
# CONNECT TO SUPABASE
# =========================================================

print("Connecting to Supabase...")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


# =========================================================
# LOAD EMBEDDING MODEL
# =========================================================

print("Loading embedding model:")
print(MODEL_NAME)

model = SentenceTransformer(MODEL_NAME)

print("Embedding model loaded.")


# =========================================================
# READ CHUNKS FROM SQLITE
# =========================================================

connection = sqlite3.connect(SQLITE_DB)
connection.row_factory = sqlite3.Row

query = """
SELECT
    chunk_id,
    source_id,
    document_id,
    document_checksum,
    source_validation_status,
    page_start,
    page_end,
    section_heading,
    text,
    chunk_type,
    run_id,
    chunking_version,
    content_hash,
    token_count,
    overlap_sentence_count,
    overlap_metadata,
    boundary_reason
FROM hierarchical_chunks
WHERE chunk_type = 'CHILD'
ORDER BY source_id, document_id, chunk_index
"""

rows = connection.execute(query).fetchall()

print(f"Loaded {len(rows)} chunks.")


if not rows:
    raise RuntimeError("No child chunks found in SQLite.")


# =========================================================
# PREPARE TEXT
# =========================================================

texts = [row["text"] for row in rows]


# =========================================================
# GENERATE EMBEDDINGS
# =========================================================

print("Generating embeddings...")

embeddings = model.encode(
    texts,
    batch_size=32,
    show_progress_bar=True,
    normalize_embeddings=True
)

print("Embeddings generated.")

print(
    f"Embedding dimension: {len(embeddings[0])}"
)


# =========================================================
# PREPARE SUPABASE RECORDS
# =========================================================

records = []

for row, embedding in zip(rows, embeddings):

    metadata = {
        "chunk_type": row["chunk_type"],
        "run_id": row["run_id"],
        "document_checksum": row["document_checksum"],
        "source_validation_status": row["source_validation_status"],
        "chunking_version": row["chunking_version"],
        "content_hash": row["content_hash"],
        "token_count": row["token_count"],
        "overlap_sentence_count": row["overlap_sentence_count"],
        "overlap_metadata": row["overlap_metadata"],
        "boundary_reason": row["boundary_reason"],
    }

    # pgvector accepts vector input in this format:
    vector_string = "[" + ",".join(
        str(float(value))
        for value in embedding
    ) + "]"

    record = {
        "chunk_id": row["chunk_id"],
        "source_id": row["source_id"],
        "document_id": row["document_id"],
        "content": row["text"],
        "page_start": row["page_start"],
        "page_end": row["page_end"],
        "section_heading": row["section_heading"],
        "authority": None,
        "topic": None,
        "metadata": metadata,
        "embedding": vector_string,
        "embedding_model": MODEL_NAME,
        "embedding_version": EMBEDDING_VERSION,
    }

    records.append(record)


# =========================================================
# UPLOAD TO SUPABASE
# =========================================================

print()
print("Uploading embeddings to Supabase...")
print(f"Total records: {len(records)}")

uploaded = 0

for start in range(0, len(records), BATCH_SIZE):

    batch = records[start:start + BATCH_SIZE]

    supabase \
        .table("knowledge_chunks") \
        .insert(batch) \
        .execute()

    uploaded += len(batch)

    print(
        f"Uploaded {uploaded}/{len(records)}"
    )


# =========================================================
# COMPLETE
# =========================================================

connection.close()

print()
print("=" * 60)
print("RAG EMBEDDING INGESTION COMPLETE")
print("=" * 60)
print(f"Chunks processed : {len(records)}")
print(f"Embeddings        : {len(records)}")
print(f"Dimensions        : {len(embeddings[0])}")
print(f"Model             : {MODEL_NAME}")
print("=" * 60)