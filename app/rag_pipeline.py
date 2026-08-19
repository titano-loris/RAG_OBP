"""
RAG Pipeline — Orchestration retriever + generator.

il coordonne. initialize() prépare les deux briques 
(générateur; ensuite échec rapide si le modèle manque — puis l'index).
query() enchaîne retrieval → génération et retourne le résultat tracé : 
réponse + documents utilisés + sources + scores + latence. 

Le pipeline ne retourne donc pas qu'une réponse, il retourne aussi les
documents utilisés, leurs sources et leurs scores desimilarité et 
c'est ce qui rend le système ÉVALUABLE :

  - les tests de fidélité comparent la réponse à context_docs
  - les tests de retrieval vérifient que la bonne source remonte
  - les scores permettent d'observer le comportement du retriever
    (souvenir de RAG-TestKit : question pertinente ≈ 0.6+, question
    hors sujet : tout plafonne sous 0.4)
  - l'interface affiche les sources : l'utilisateur peut vérifier

Un système IA sans traçabilité n'est pas testable. La structure de
retour est donc une décision d'architecture QA, pas un détail.
═══════════════════════════════════════════════════════════════════
"""
import logging
import time

from app.generator import Generator
from app.retriever import Retriever

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    Pipeline complet : question → retrieval → génération → réponse tracée.

    Usage:
        pipeline = RAGPipeline()
        pipeline.initialize()
        result = pipeline.query("Comment lister les comptes d'une banque ?")
        print(result["answer"])
        print(result["sources"])
    """

    def __init__(self):
        self.retriever: Retriever | None = None
        self.generator: Generator | None = None
        self._initialized = False

    def initialize(self) -> None:
        """
        Prépare les deux composants. À appeler une seule fois.

        """
        logger.info("Initialisation du pipeline RAG...")
        self.generator = Generator()
        self.generator.check_availability()

        self.retriever = Retriever()
        self.retriever.build_index()

        self._initialized = True
        logger.info("Pipeline RAG prêt.")

    def query(self, question: str) -> dict:
        """
        Traite une question de bout en bout.

        Returns:
            {
                "question": str,
                "answer": str,
                "context_docs": list[str],   # contenus utilisés (→ tests fidélité)
                "sources": list[str],        # URLs des endpoints (→ affichage UI)
                "retrieval_scores": list[float],
                "latency_seconds": float,
            }
        """
        if not self._initialized:
            raise RuntimeError("Pipeline non initialisé. Appeler initialize() d'abord.")

        start = time.perf_counter()

        retrieved = self.retriever.retrieve(question)
        context_docs = [doc["content"] for doc in retrieved]
        sources = [doc["source"] for doc in retrieved]
        scores = [round(doc["score"], 3) for doc in retrieved]

        answer = self.generator.generate(question, context_docs)

        return {
            "question": question,
            "answer": answer,
            "context_docs": context_docs,
            "sources": sources,
            "retrieval_scores": scores,
            "latency_seconds": round(time.perf_counter() - start, 2),
        }
