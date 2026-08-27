"""
Dimensions 1 & 3 — Fidélité au contexte et exactitude technique.

═══════════════════════════════════════════════════════════════════
DIMENSION 1 — FIDÉLITÉ
La réponse s'appuie-t-elle réellement sur les documents récupérés,
sans y ajouter d'information ?

Approche retenue : DÉTERMINISTE. On vérifie que les endpoints cités
dans la réponse existent bel et bien dans le contexte fourni. C'est
mesurable exactement, sans juge LLM — donc reproductible en CI.
(Leçon de DeepEval-Lab : un juge 3B présente un biais systématique
de confusion contexte/sortie sur la métrique Faithfulness.)

═══════════════════════════════════════════════════════════════════
DIMENSION 3 — EXACTITUDE TECHNIQUE
Les détails cités sont-ils corrects ? En contexte bancaire, un
endpoint inventé ou une méthode HTTP erronée bloque un développeur —
ou pire, l'oriente vers un appel destructeur. C'est la dimension la
plus critique du projet.
═══════════════════════════════════════════════════════════════════
"""
import re

import pytest

# Un endpoint OBP dans une réponse : /obp/vX.Y.Z/...
ENDPOINT_PATTERN = re.compile(r"/obp/v[\d.]+/[\w\-{}/]*")


def extract_endpoints(text: str) -> set[str]:
    """Extrait les chemins d'endpoints cités dans un texte."""
    return {m.rstrip("/.,;:") for m in ENDPOINT_PATTERN.findall(text)}


@pytest.mark.evaluation
@pytest.mark.slow
class TestFaithfulness:
    """La réponse reste ancrée dans les documents récupérés."""

    def test_cited_endpoints_exist_in_context(self, ask, golden):
        """
        Tout endpoint cité dans la réponse doit apparaître dans le
        contexte. Un endpoint absent du contexte est une fabrication —
        le cas le plus dangereux en contexte bancaire.
        """
        fabrications = []

        for case in golden["in_scope"]:
            result = ask(case["question"])
            context = " ".join(result["context_docs"])

            cited = extract_endpoints(result["answer"])
            context_endpoints = extract_endpoints(context)

            for endpoint in cited:
                # Correspondance souple : le modèle peut tronquer une URL
                if not any(endpoint in ce or ce in endpoint for ce in context_endpoints):
                    fabrications.append(
                        f"[{case['id']}] '{case['question']}'\n"
                        f"  Endpoint cité mais absent du contexte : {endpoint}"
                    )

        assert not fabrications, (
            f"{len(fabrications)} endpoint(s) fabriqué(s) :\n\n" + "\n\n".join(fabrications)
        )

    def test_answers_are_not_empty(self, ask, golden):
        """Une question dans le périmètre doit produire une réponse substantielle."""
        for case in golden["in_scope"]:
            result = ask(case["question"])
            assert len(result["answer"].strip()) > 40, (
                f"[{case['id']}] Réponse trop courte : {result['answer']!r}"
            )

    def test_context_is_always_provided(self, ask, golden):
        """
        La traçabilité est une exigence structurelle : sans documents
        de contexte retournés, aucune évaluation de fidélité n'est possible.
        """
        for case in golden["in_scope"]:
            result = ask(case["question"])
            assert result["context_docs"], f"[{case['id']}] Aucun document de contexte"
            assert result["sources"], f"[{case['id']}] Aucune source tracée"


@pytest.mark.evaluation
@pytest.mark.slow
class TestTechnicalAccuracy:
    """Les détails techniques cités correspondent à la documentation."""

    def test_expected_terms_are_present(self, ask, golden):
        """
        Pour chaque question de référence, la réponse doit contenir au
        moins un des termes techniques attendus.
        """
        failures = []

        for case in golden["in_scope"]:
            result = ask(case["question"])
            answer_lower = result["answer"].lower()

            if not any(t.lower() in answer_lower for t in case["must_contain_any"]):
                failures.append(
                    f"[{case['id']}] '{case['question']}'\n"
                    f"  Attendu (un parmi) : {case['must_contain_any']}\n"
                    f"  Obtenu : {result['answer'][:200]}"
                )

        assert not failures, (
            f"{len(failures)} réponse(s) sans le terme technique attendu :\n\n"
            + "\n\n".join(failures)
        )

    def test_retrieval_returns_relevant_source(self, ask, golden):
        """
        Le retriever doit remonter une source cohérente avec la question.

        Ce test évalue la BRIQUE RETRIEVAL, distinctement de la génération :
        une réponse juste issue de mauvaises sources reste un défaut —
        c'est précisément le bug détecté lors de l'expérience cross-lingue.
        """
        failures = []

        for case in golden["in_scope"]:
            result = ask(case["question"])
            expected = case["expected_source_contains"].lower()
            sources = [s.lower() for s in result["sources"]]

            if not any(expected in s for s in sources):
                failures.append(
                    f"[{case['id']}] '{case['question']}'\n"
                    f"  Source attendue contenant : '{expected}'\n"
                    f"  Sources obtenues : {result['sources']}\n"
                    f"  Scores : {result['retrieval_scores']}"
                )

        assert not failures, (
            f"{len(failures)} retrieval(s) hors sujet :\n\n" + "\n\n".join(failures)
        )

    def test_retrieval_scores_are_discriminant(self, ask, golden):
        """
        Le score du meilleur document doit dépasser un seuil de pertinence.

        Référence mesurée : questions en anglais ≈ 0,65 ; questions hors
        périmètre ≈ 0,32. Un seuil à 0,45 sépare les deux régimes.
        Ce test détecterait une régression du type cross-lingue.
        """
        weak = []

        for case in golden["in_scope"]:
            result = ask(case["question"])
            top_score = result["retrieval_scores"][0] if result["retrieval_scores"] else 0

            if top_score < 0.45:
                weak.append(
                    f"[{case['id']}] score {top_score} — '{case['question']}'"
                )

        assert not weak, (
            "Retrieval faiblement discriminant (seuil 0.45) :\n" + "\n".join(weak)
        )
