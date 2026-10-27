
from flask import Flask, request, jsonify
from flask_cors import CORS

from rag import ask_kisansathi


# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)

# Allow React frontend to communicate with Flask
CORS(app)


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/api/health", methods=["GET"])
def health():

    return jsonify({
        "status": "ok",
        "service": "KisanSathi RAG API"
    })


# ============================================================
# ASK KISANSATHI
# ============================================================

@app.route("/api/ask", methods=["POST"])
def ask():

    try:

        # ----------------------------------------------------
        # Read request
        # ----------------------------------------------------

        data = request.get_json()

        if not data:

            return jsonify({
                "error": "Request body is required"
            }), 400


        # ----------------------------------------------------
        # Get question
        # ----------------------------------------------------

        question = data.get(
            "question",
            ""
        ).strip()


        # ----------------------------------------------------
        # Get requested language
        # ----------------------------------------------------

        language = data.get(
            "language",
            "English"
        )


        # ----------------------------------------------------
        # Validate question
        # ----------------------------------------------------

        if not question:

            return jsonify({
                "error": "Question is required"
            }), 400


        # ----------------------------------------------------
        # Complete RAG pipeline
        #
        # question
        #    ↓
        # embedding
        #    ↓
        # pgvector retrieval
        #    ↓
        # 15 candidates
        #    ↓
        # CrossEncoder reranking
        #    ↓
        # top 5
        #    ↓
        # Groq
        #    ↓
        # answer + sources
        # ----------------------------------------------------

        result = ask_kisansathi(
            question=question,
            language=language
        )


        # ----------------------------------------------------
        # Return result to React
        # ----------------------------------------------------

        return jsonify(result)


    except Exception as e:

        print("\n" + "=" * 70)
        print("KISANSATHI API ERROR")
        print("=" * 70)

        print(str(e))

        print("=" * 70)


        return jsonify({
            "error": "Something went wrong while processing your question.",
            "details": str(e)
        }), 500


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
