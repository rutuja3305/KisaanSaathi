import os

from dotenv import load_dotenv
from sentence_transformers import CrossEncoder, SentenceTransformer
from supabase import create_client
from groq import Groq


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL is missing from .env")

if not SUPABASE_KEY:
    raise ValueError("SUPABASE_KEY is missing from .env")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is missing from .env")


# ============================================================
# CLIENTS
# ============================================================

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

groq = Groq(
    api_key=GROQ_API_KEY
)


# ============================================================
# MODELS
# ============================================================

print("Loading embedding model...")

embedding_model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)

print("Loading reranker...")

reranker = CrossEncoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)

print("RAG models loaded.")


# ============================================================
# STEP 1 — VECTOR RETRIEVAL
# ============================================================

def retrieve_chunks(question, match_count=15):

    """
    Retrieve candidate chunks from Supabase pgvector.

    Flow:

        User question
              ↓
        SentenceTransformer
              ↓
        384-dimensional embedding
              ↓
        Supabase pgvector
              ↓
        15 candidate chunks
    """

    query_embedding = embedding_model.encode(
        question
    ).tolist()

    result = supabase.rpc(
        "match_knowledge_chunks",
        {
            "query_embedding": query_embedding,
            "match_count": match_count
        }
    ).execute()

    return result.data or []


# ============================================================
# STEP 2 — RERANK
# ============================================================

def rerank_chunks(question, chunks, top_k=5):

    """
    Rerank the retrieved chunks using CrossEncoder.

    Example:

        15 retrieved chunks
                 ↓
            CrossEncoder
                 ↓
          relevance scores
                 ↓
             top 5 chunks
    """

    if not chunks:
        return []

    pairs = []

    for chunk in chunks:

        content = chunk.get("content", "")

        pairs.append(
            (
                question,
                content
            )
        )

    scores = reranker.predict(pairs)

    ranked_chunks = []

    for chunk, score in zip(chunks, scores):

        chunk_copy = dict(chunk)

        chunk_copy["rerank_score"] = float(score)

        ranked_chunks.append(chunk_copy)

    ranked_chunks.sort(
        key=lambda item: item["rerank_score"],
        reverse=True
    )

    return ranked_chunks[:top_k]


# ============================================================
# STEP 3 — BUILD CONTEXT
# ============================================================

def build_context(chunks):

    """
    Convert the top chunks into clean context for the LLM.
    """

    context_parts = []

    for i, chunk in enumerate(chunks, start=1):

        context_parts.append(
            f"""
SOURCE {i}

Source ID:
{chunk.get("source_id")}

Document ID:
{chunk.get("document_id")}

Section:
{chunk.get("section_heading")}

CONTENT:
{chunk.get("content")}
"""
        )

    return "\n".join(context_parts)


# ============================================================
# STEP 4 — GENERATE ANSWER
# ============================================================

def generate_answer(
    question,
    chunks,
    language="English"
):

    """
    Generate a grounded answer using only the retrieved
    official context.
    """

    if not chunks:

        return (
            "I could not find enough information in the "
            "available official sources."
        )

    context = build_context(chunks)

    prompt = f"""
You are KisanSathi, a reliable AI assistant for Indian farmers.

Your job is to answer the farmer's question using ONLY the
official source context provided below.

IMPORTANT RULES:

1. Use ONLY the provided official source context.
2. Do NOT invent facts.
3. Do NOT use outside knowledge.
4. If the sources do not contain enough information,
   clearly say that the available official sources do not
   provide enough information.
5. Give a simple and farmer-friendly explanation.
6. Avoid unnecessary technical terminology.
7. Answer completely in the requested language.
8. Do NOT mention embeddings.
9. Do NOT mention pgvector.
10. Do NOT mention Supabase.
11. Do NOT mention reranking.
12. Do NOT mention chunks.
13. Do NOT mention the RAG pipeline.
14. Do NOT expose internal similarity or reranking scores.
15. Do NOT include page numbers in the farmer-facing answer.
16. Do NOT invent a source that is not present in the context.

REQUESTED LANGUAGE:
{language}

USER QUESTION:
{question}

OFFICIAL SOURCE CONTEXT:
{context}

Provide a clear, concise and useful answer for an Indian farmer.

At the end, include:

Sources:
- Name/description of the relevant official source

Do not include page numbers.
Do not include internal document IDs unless necessary.
"""

    response = groq.chat.completions.create(

        model="openai/gpt-oss-20b",

        messages=[
            {
                "role": "system",
                "content": (
                    "You are a reliable, evidence-grounded "
                    "agricultural information assistant. "
                    "Never fabricate information."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],

        temperature=0.1
    )

    return response.choices[0].message.content


# ============================================================
# STEP 5 — SOURCE METADATA
# ============================================================

def build_sources(chunks):

    """
    Prepare clean source information for the frontend.

    Internal database IDs are not intended to be shown
    directly to farmers.
    """

    sources = []

    seen = set()

    for chunk in chunks:

        source_id = chunk.get("source_id")
        document_id = chunk.get("document_id")
        section = chunk.get("section_heading")

        key = (
            source_id,
            document_id
        )

        if key in seen:
            continue

        seen.add(key)

        sources.append(
            {
                "source_id": source_id,
                "document_id": document_id,
                "section": section
            }
        )

    return sources


# ============================================================
# MAIN RAG FUNCTION
# ============================================================

def ask_kisansathi(
    question,
    language="English"
):

    """
    Complete KisanSathi RAG pipeline.

    Question
       ↓
    Retrieval
       ↓
    15 candidates
       ↓
    Reranking
       ↓
    Top 5
       ↓
    Groq
       ↓
    Answer + Sources
    """

    question = question.strip()

    if not question:

        return {
            "answer": "Please enter a question.",
            "sources": [],
            "retrieved_count": 0,
            "reranked_count": 0,
            "language": language
        }

    # --------------------------------------------------------
    # RETRIEVAL
    # --------------------------------------------------------

    retrieved_chunks = retrieve_chunks(
        question,
        match_count=15
    )

    if not retrieved_chunks:

        return {
            "answer": (
                "I could not find enough information in "
                "the available official sources."
            ),
            "sources": [],
            "retrieved_count": 0,
            "reranked_count": 0,
            "language": language
        }

    # --------------------------------------------------------
    # RERANKING
    # --------------------------------------------------------

    ranked_chunks = rerank_chunks(
        question,
        retrieved_chunks,
        top_k=5
    )

    # --------------------------------------------------------
    # GENERATION
    # --------------------------------------------------------

    answer = generate_answer(
        question,
        ranked_chunks,
        language=language
    )

    # --------------------------------------------------------
    # SOURCES
    # --------------------------------------------------------

    sources = build_sources(
        ranked_chunks
    )

    return {
        "answer": answer,
        "sources": sources,
        "retrieved_count": len(retrieved_chunks),
        "reranked_count": len(ranked_chunks),
        "language": language
    }


# ============================================================
# COMMAND-LINE TESTING
# ============================================================

def ask(question):

    """
    Optional terminal testing function.
    The website will use ask_kisansathi() instead.
    """

    print("\n" + "=" * 70)
    print("KISANSATHI")
    print("=" * 70)

    print("\nRetrieving official sources...")

    result = ask_kisansathi(
        question,
        language="English"
    )

    print(
        f"Retrieved {result['retrieved_count']} chunks."
    )

    print(
        f"Using top {result['reranked_count']} chunks."
    )

    print("\n" + "=" * 70)
    print("ANSWER")
    print("=" * 70)

    print(result["answer"])

    print("\n" + "=" * 70)
    print("SOURCES")
    print("=" * 70)

    for source in result["sources"]:

        print(
            f"- {source.get('source_id')}"
        )


if __name__ == "__main__":

    question = input(
        "\nAsk KisanSathi: "
    )

    ask(question)