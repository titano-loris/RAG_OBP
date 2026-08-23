# PR: fix/remove-empty-state

## Titre suggéré
fix(ui): remove empty-state element when messages present (playwright test)

## Description
Contexte : les tests Playwright attendaient la disparition de l’élément d’état vide (`data-testid="empty-state"`) après envoi d’un message. L’élément restait présent dans le DOM, provoquant un échec du test `test_full_conversation_flow`.

Changements :
- `app.js` : la fonction `updateEmptyState()` supprime désormais l'élément `empty-state` du DOM lorsqu'un message est ajouté, et le recrée si l'historique redevient vide.

Pourquoi : corrige un faux négatif dans la suite d'intégration d'interface (Playwright) sans impacter l'expérience utilisateur visible.

Tests réalisés localement :
- Installation des dépendances de test : `pytest-playwright`, `playwright`, `requests`.
- Installation du navigateur Chromium pour Playwright.
- Démarrage du serveur : `python app.py` (écoute par défaut sur http://0.0.0.0:8000)
- Exécution de la suite UI : `pytest tests_ui/` → Résultat : `5 passed, 0 failed`.

### Remarque
Si tu préfères masquer l'élément via CSS (`.hidden`) plutôt que le supprimer du DOM, je peux adapter la PR.

## Étapes pour vérifier localement
```powershell
# 1. Récupérer la branche
git fetch origin
git checkout fix/remove-empty-state

# 2. (optionnel) activer l'environnement virtuel et installer dépendances
python -m venv .venv
. .venv/Scripts/Activate.ps1
pip install -r requirements.txt
pip install pytest-playwright playwright requests
python -m playwright install chromium

# 3. Démarrer le serveur (terminal 1)
python app.py

# 4. Lancer les tests (terminal 2)
pytest tests_ui/ -q
```

## Message court à poster au reviser / collaborateur
Bonjour — j’ai corrigé un petit problème d’UI qui faisait échouer un test Playwright (élément `empty-state` restait dans le DOM après envoi). J’ai poussé la branche `fix/remove-empty-state`. Tous les tests UI passent localement (`5 passed`).

Lien PR (à créer via l'interface si tu n'as pas de token) :
https://github.com/titano-loris/RAG_OBP/pull/new/fix/remove-empty-state

---

Fait par l'automatisation : branche créée et poussée, tests exécutés localement, correctif appliqué et commité.
