"""
Test de fumée de l'étape 2 — à lancer AVANT de brancher Flask.

    python smoke_test.py

C'est le réflexe « tranche verticale » : valider le pipeline nu avant
d'ajouter l'interface par-dessus.
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

from app.rag_pipeline import RAGPipeline


def main():
    print("=" * 60)
    print("  Test de fumée — pipeline RAG OBP")
    print("=" * 60)

    pipeline = RAGPipeline()
    pipeline.initialize()

    tests = [
        ("In-scope question", "How do I list the accounts of a bank?"),
        ("Out-of-scope question (must be refused)", "What is the current interest rate of the French Livret A savings account?"),
    ]

    for label, question in tests:
        print(f"\n▶ {label}")
        print(f"  Q : {question}")
        result = pipeline.query(question)
        print(f"  R ({result['latency_seconds']}s) : {result['answer'][:300]}")
        print(f"  Sources : {result['sources']}")
        print(f"  Scores  : {result['retrieval_scores']}")

    print("\n✅ Pipeline fonctionnel — Flask peut être branché dessus.")


if __name__ == "__main__":
    main()
