"""
Retriever — Recherche sémantique dans la documentation OBP.

Le même modèle d'embeddings (MiniLM, 384 dimensions) transforme :
  - les 129 documents OBP, une fois, au démarrage    → indexés dans FAISS
  - chaque question de l'utilisateur, à la volée      → comparée à l'index

Comme le « traducteur » est identique des deux côtés, les vecteurs
sont comparables : deux textes de sens proche atterrissent au même
endroit de l'espace à 384 dimensions, même sans mots en commun.

NOTE SUR LE CHUNKING : un RAG classique découpe ses documents en
morceaux (chunks) de taille fixe. Ici, ce n'est pas nécessaire :
chaque document EST déjà une unité sémantique naturelle (un endpoint
= un sujet). C'est un avantage du travail fait à l'étape 1 — la
granularité de la base a été pensée en amont, pas subie.
"""
import json
import logging
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
KNOWLEDGE_PATH = Path(__file__).parent.parent / "datasets" / "obp_knowledge.json"
TOP_K = 3  # nombre de documents remontés par question


class Retriever:
    """
    Moteur de recherche sémantique sur la doc OBP.

    Usage:
        retriever = Retriever()
        retriever.build_index()
        docs = retriever.retrieve("Comment lister les comptes ?")
    """

    def __init__(self, embedding_model: str = EMBEDDING_MODEL):
        logger.info(f"Chargement du modèle d'embeddings : {embedding_model}")
        self.embedder = SentenceTransformer(embedding_model)
        self.index: faiss.IndexFlatIP | None = None
        self.documents: list[dict] = []

    def build_index(self, path: Path = KNOWLEDGE_PATH) -> None:
        """
        Charge les documents et construit l'index FAISS.

        normalize_embeddings=True est essentiel : avec des vecteurs
        normalisés, le produit scalaire (IndexFlatIP) équivaut à la
        similarité cosinus — la mesure standard pour comparer du sens.
        Sans normalisation, les scores seraient biaisés par la longueur
        des textes plutôt que par leur signification.
        """
        with open(path, encoding="utf-8") as f:
            self.documents = json.load(f)
        if not self.documents:
            raise ValueError(f"Base de connaissances vide : {path}")

        texts = [doc["content"] for doc in self.documents]
        embeddings = self.embedder.encode(
            texts, normalize_embeddings=True, show_progress_bar=False
        )

        # La dimension est lue depuis le modèle (384 pour MiniLM) plutôt
        # qu'écrite en dur : changer de modèle ne casse rien.
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(np.array(embeddings, dtype=np.float32))

        logger.info(
            f"Index FAISS prêt : {len(self.documents)} documents, dim={dimension}"
        )

    def retrieve(self, query: str, top_k: int = TOP_K) -> list[dict]:
        """
        Retourne les top_k documents les plus proches de la question.

        Returns:
            [{"content", "source", "summary", "score"}, ...]
            triés par similarité décroissante (score ∈ [0, 1] environ).
        """
        if self.index is None:
            raise RuntimeError("Index non construit. Appeler build_index() d'abord.")
        if not query or not query.strip():
            return []

        query_vec = self.embedder.encode(
            [query], normalize_embeddings=True, show_progress_bar=False
        )
        scores, indices = self.index.search(
            np.array(query_vec, dtype=np.float32), top_k
        )

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:  # moins de documents que top_k
                continue
            doc = self.documents[idx]
            results.append(
                {
                    "content": doc["content"],
                    "source": doc.get("source", "unknown"),
                    "summary": doc.get("summary", ""),
                    "score": float(score),
                }
            )
        return results
