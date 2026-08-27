"""
Dimension 2 — Anti-hallucination.

═══════════════════════════════════════════════════════════════════
LE COMPORTEMENT ÉVALUÉ
Le modèle refuse-t-il de répondre lorsque l'information n'est pas
dans sa base documentaire ?

C'est le comportement le plus difficile à obtenir d'un LLM : Mistral
CONNAÎT le taux du Livret A et la capitale de l'Australie par son
entraînement. La règle 3 du prompt système lui impose de refuser
malgré tout. Ces tests vérifient ce contrat.

En contexte bancaire, l'enjeu est direct : un assistant qui invente
un endpoint ou une règle métier plausible est plus dangereux qu'un
assistant qui reconnaît ses limites.
═══════════════════════════════════════════════════════════════════
"""
import pytest


@pytest.mark.evaluation
@pytest.mark.slow
class TestOutOfScopeRefusal:
    """Le modèle refuse ce qui n'est pas dans la documentation."""

    def test_out_of_scope_questions_are_refused(self, ask, golden):
        """
        Chaque question hors périmètre doit produire un refus explicite.
        La détection s'appuie sur les marqueurs de refus du prompt système.
        """
        hallucinations = []
        markers = [m.lower() for m in golden["refusal_markers"]]

        for case in golden["out_of_scope"]:
            result = ask(case["question"])
            answer_lower = result["answer"].lower()

            if not any(m in answer_lower for m in markers):
                hallucinations.append(
                    f"[{case['id']}] ({case['category']}) '{case['question']}'\n"
                    f"  Réponse au lieu d'un refus : {result['answer'][:250]}"
                )

        assert not hallucinations, (
            f"{len(hallucinations)} HALLUCINATION(S) — le modèle a répondu "
            f"hors de sa base documentaire :\n\n" + "\n\n".join(hallucinations)
        )

    def test_no_endpoint_invented_on_out_of_scope(self, ask, golden):
        """
        Une question hors périmètre ne doit produire AUCUN endpoint.
        Citer un endpoint pour justifier une réponse hors base serait
        la forme la plus trompeuse d'hallucination.
        """
        from tests_ai.test_faithfulness import extract_endpoints

        leaks = []
        for case in golden["out_of_scope"]:
            result = ask(case["question"])
            endpoints = extract_endpoints(result["answer"])
            if endpoints:
                leaks.append(f"[{case['id']}] endpoints cités : {endpoints}")

        assert not leaks, (
            "Endpoints cités sur des questions hors périmètre :\n" + "\n".join(leaks)
        )


@pytest.mark.evaluation
@pytest.mark.slow
class TestRetrievalSignal:
    """Le score de retrieval reflète-t-il la pertinence de la question ?"""

    def test_out_of_scope_scores_are_lower(self, ask, golden):
        """
        Les questions hors périmètre doivent obtenir des scores de
        similarité nettement inférieurs aux questions pertinentes.

        Mesure de référence (voir EXPERIMENTS.md) :
          questions pertinentes  ≈ 0,65
          questions hors sujet   ≈ 0,32
        Ce delta est exploitable comme signal de détection automatique —
        une piste d'amélioration documentée du projet.
        """
        in_scope_scores = [
            ask(c["question"])["retrieval_scores"][0]
            for c in golden["in_scope"]
            if ask(c["question"])["retrieval_scores"]
        ]
        out_scores = [
            ask(c["question"])["retrieval_scores"][0]
            for c in golden["out_of_scope"]
            if ask(c["question"])["retrieval_scores"]
        ]

        avg_in = sum(in_scope_scores) / len(in_scope_scores)
        avg_out = sum(out_scores) / len(out_scores)

        assert avg_in > avg_out, (
            f"Le retrieval ne discrimine pas : "
            f"pertinentes {avg_in:.3f} vs hors sujet {avg_out:.3f}"
        )
        assert avg_in - avg_out > 0.15, (
            f"Delta insuffisant ({avg_in - avg_out:.3f}) entre questions "
            f"pertinentes ({avg_in:.3f}) et hors sujet ({avg_out:.3f}). "
            f"Signe d'une dégradation du retrieval."
        )
