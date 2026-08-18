"""
Interface web de l'assistant Open Banking.

Rôle : exposer le pipeline RAG via une page web et une API HTTP.
C'est la CIBLE des deux couches de test :
  - tests_ui/  interroge cette interface via le navigateur (Playwright)
  - tests_ai/  interroge le pipeline RAG directement (sans passer par le web)
le fichier templates/index.html, reçoit les questions, valide les entrées (vide → 400, trop long → 400), 
appelle le pipeline, gère les erreurs (500 avec message lisible)et offre 
la sonde /api/health pour les tests Playwright.

"""
import logging

from flask import Flask, jsonify, render_template, request

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Le pipeline est chargé une seule fois au démarrage (le modèle pèse plusieurs Go).
# Chargement paresseux : la première requête déclenche l'initialisation.
_pipeline = None


def get_pipeline():
    """Retourne le pipeline RAG, en l'initialisant au premier appel."""
    global _pipeline
    if _pipeline is None:
        from app.rag_pipeline import RAGPipeline

        logger.info("Initialisation du pipeline RAG (peut prendre plusieurs minutes)...")
        _pipeline = RAGPipeline()
        _pipeline.initialize()
        logger.info("Pipeline prêt.")
    return _pipeline


@app.route("/")
def home():
    """Sert la page de l'assistant."""
    return render_template("index.html")


@app.route("/api/health")
def health():
    """
    Sonde de disponibilité.

    Utile aux tests d'interface : Playwright peut attendre que le modèle
    soit chargé avant de lancer les scénarios, plutôt que d'échouer sur
    un timeout au premier message.
    """
    return jsonify({"status": "ok", "model_loaded": _pipeline is not None})


@app.route("/api/ask", methods=["POST"])
def ask():
    """
    Traite une question et retourne la réponse du pipeline RAG.

    Corps attendu  : {"question": "..."}
    Réponse (200)  : {"answer": "...", "sources": [...], "latency_seconds": 12.3}
    Réponse (400)  : {"error": "..."} si la question est vide
    Réponse (500)  : {"error": "..."} si le pipeline échoue

    La validation et la gestion d'erreur sont explicites : les tests UI
    vérifient qu'un message clair remonte à l'utilisateur dans chaque cas,
    plutôt qu'une page blanche ou une trace technique.
    """
    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or "").strip()

    if not question:
        return jsonify({"error": "La question ne peut pas être vide."}), 400

    if len(question) > 2000:
        return jsonify({"error": "Question trop longue (2000 caractères maximum)."}), 400

    try:
        result = get_pipeline().query(question)
        return jsonify(
            {
                "answer": result["answer"],
                "sources": result.get("sources", []),
                "latency_seconds": result.get("latency_seconds", 0),
            }
        )
    except Exception as exc:
        logger.exception("Échec du pipeline RAG")
        return jsonify({"error": f"Le service est momentanément indisponible."}), 500


if __name__ == "__main__":
    # debug=False : le rechargement automatique relancerait le chargement du modèle
    app.run(host="127.0.0.1", port=5000, debug=False)