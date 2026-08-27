"""
Serveur web de l'assistant Open Banking.

INTÉGRATION : reprend l'interface et l'ergonomie livrées par la couche UI
(structure du chat, indicateur de saisie, gestion d'erreur) en les branchant
sur le pipeline RAG réel — FAISS + Mistral-7B — au lieu du stub par mots-clés
utilisé pendant le développement parallèle.

Choix conservés depuis la contribution UI :
  - port 8000
  - route POST /api/chat avec charge utile {"message": "..."}
  - fichiers statiques index.html / styles.css / app.js

Choix repris de la branche pipeline :
  - Flask (au lieu de http.server) pour la validation et la gestion d'erreur
  - chargement paresseux du modèle : le serveur démarre immédiatement,
    le modèle se charge à la première question
  - sonde /health enrichie : indique si le modèle est prêt, ce qui permet
    aux tests d'interface d'attendre plutôt que d'échouer en timeout
"""
import logging
import sys
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory

sys.path.insert(0, str(Path(__file__).resolve().parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder="static", template_folder="templates")

MAX_QUESTION_LENGTH = 2000

_pipeline = None


def get_pipeline():
    """
    Retourne le pipeline RAG, en l'initialisant au premier appel.

    Le modèle pèse ~14 Go : le charger au démarrage rendrait le serveur
    indisponible plusieurs minutes. Le chargement paresseux permet à
    l'interface d'être servie immédiatement.
    """
    global _pipeline
    if _pipeline is None:
        from app.rag_pipeline import RAGPipeline

        logger.info("Initialisation du pipeline RAG (plusieurs minutes)...")
        _pipeline = RAGPipeline()
        _pipeline.initialize()
        logger.info("Pipeline prêt.")
    return _pipeline


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/styles.css")
def styles():
    return send_from_directory("static", "styles.css", mimetype="text/css")


@app.route("/app.js")
def script():
    return send_from_directory("static", "app.js", mimetype="application/javascript")


@app.route("/health")
def health():
    """
    Sonde de disponibilité.

    model_loaded=False signifie que le serveur répond mais que la première
    question déclenchera un chargement long — information utile aux tests.
    """
    return jsonify({"status": "ok", "model_loaded": _pipeline is not None})


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Traite une question et retourne la réponse du pipeline RAG.

    Requête  : {"message": "..."}
    200      : {"answer", "sources", "scores", "latency_seconds"}
    400      : {"error"} — question vide ou trop longue
    500      : {"error"} — défaillance du pipeline

    Les champs sources et scores exposent la traçabilité du retrieval :
    ils alimentent l'affichage et servent de base aux tests d'évaluation.
    """
    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()

    if not message:
        return jsonify({"error": "Please enter a question."}), 400

    if len(message) > MAX_QUESTION_LENGTH:
        return jsonify(
            {"error": f"Question too long (max {MAX_QUESTION_LENGTH} characters)."}
        ), 400

    try:
        result = get_pipeline().query(message)
        return jsonify(
            {
                "answer": result["answer"],
                "sources": result.get("sources", []),
                "scores": result.get("retrieval_scores", []),
                "latency_seconds": result.get("latency_seconds", 0),
            }
        )
    except Exception:
        logger.exception("Échec du pipeline RAG")
        return jsonify({"error": "Service temporarily unavailable. Please try again."}), 500


if __name__ == "__main__":
    # debug=False : le rechargement automatique relancerait le chargement du modèle
    app.run(host="127.0.0.1", port=8000, debug=False)
