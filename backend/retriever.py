import os

from dotenv import load_dotenv
from supabase import create_client
from sentence_transformers import SentenceTransformer


# =========================================================
# CONFIG
# =========================================================

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


# =========================================================
# VALIDATION
# =========================================================

if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL is missing from .env")

if not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_KEY is missing from .env")


# =========================================================
# INITIALIZE
# =========================================================

print("Loading embedding model...")

model = SentenceTransformer(MODEL_NAME)

print("Embedding model ready.")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


# =========================================================
# RETRIEVER
# =========================================================

def retrieve(
    question: str,
    match_count: int = 5
) -> list[dict]:

    if not question.strip():
        return []

    # -----------------------------------------------------
    # 1. Convert question to embedding
    # -----------------------------------------------------

    query_embedding = model.encode(
        question,
        normalize_embeddings=True
    )

    # Convert numpy array → normal Python list
    query_embedding = query_embedding.tolist()

    # -----------------------------------------------------
    # 2. Search Supabase pgvector
    # -----------------------------------------------------

    response = (
        supabase
        .rpc(
            "match_knowledge_chunks",
            {
                "query_embedding": query_embedding,
                "match_count": match_count,
            }
        )
        .execute()
    )

    # -----------------------------------------------------
    # 3. Return retrieved chunks
    # -----------------------------------------------------

    return response.data or []


# =========================================================
# SIMPLE CLI
# =========================================================

if __name__ == "__main__":

    question = input("\nAsk KisanSathi: ").strip()

    results = retrieve(question, match_count=5)

    print()
    print("=" * 70)
    print("RETRIEVED CONTEXT")
    print("=" * 70)

    if not results:
        print("No relevant chunks found.")
    else:

        for index, result in enumerate(results, start=1):

            print()
            print(f"RESULT {index}")
            print("-" * 70)

            print("Source:", result.get("source_id"))
            print("Document:", result.get("document_id"))
            print(
                "Pages:",
                result.get("page_start"),
                "-",
                result.get("page_end")
            )
            print(
                "Section:",
                result.get("section_heading")
            )
            print(
                "Similarity:",
                round(
                    float(result.get("similarity", 0)),
                    4
                )
            )

            print()
            print(result.get("content", ""))

    print()
    print("=" * 70)