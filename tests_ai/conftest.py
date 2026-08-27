"""
Fixtures de la couche d'évaluation du modèle.

═══════════════════════════════════════════════════════════════════
PÉRIMÈTRE : cette couche n'utilise NI Flask NI navigateur.
Elle importe le pipeline et l'interroge directement en Python.
Ce que l'interface affiche ne la concerne pas : elle évalue ce que
le modèle DIT. La couche tests_ui/ fait l'inverse.
═══════════════════════════════════════════════════════════════════

Architecture mémoire : le pipeline est en scope "session". Le modèle
(~14 Go) n'est chargé qu'UNE fois pour toute la suite. Sans cela,
chaque test rechargerait Mistral pendant 3 à 5 minutes.

Cache des réponses : chaque appel au modèle coûte ~200 s sur CPU.
Plusieurs dimensions évaluent la MÊME réponse sous des angles
différents (une réponse est à la fois fidèle, exacte et sûre). Le
cache garantit qu'une question donnée n'est posée qu'une seule fois
pour toute la suite — c'est ce qui rend la suite exécutable.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DATA_DIR = Path(__file__).resolve().parent


# ---------- Jeux de données (légers) ----------

@pytest.fixture(scope="session")
def golden() -> dict:
    """Questions de référence : dans le périmètre et hors périmètre."""
    with open(DATA_DIR / "golden_dataset.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def adversarial() -> dict:
    """Attaques et cas limites."""
    with open(DATA_DIR / "adversarial_inputs.json", encoding="utf-8") as f:
        return json.load(f)


# ---------- Pipeline et cache (lourds) ----------

@pytest.fixture(scope="session")
def pipeline():
    """
    Pipeline RAG initialisé une seule fois.
    ATTENTION : charge Mistral-7B en mémoire (~14 Go, 3-5 min).
    """
    from app.rag_pipeline import RAGPipeline

    p = RAGPipeline()
    p.initialize()
    return p


@pytest.fixture(scope="session")
def ask(pipeline):
    """
    Interroge le pipeline avec mise en cache par question.

    Retourne une fonction : ask("question") -> dict complet du pipeline
    (answer, context_docs, sources, retrieval_scores, latency_seconds).

    Le cache est indispensable : sans lui, une suite de 15 tests
    représenterait plus d'une heure d'inférence.
    """
    cache: dict[str, dict] = {}

    def _ask(question: str) -> dict:
        if question not in cache:
            cache[question] = pipeline.query(question)
        return cache[question]

    return _ask
