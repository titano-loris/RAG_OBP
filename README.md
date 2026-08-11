# RAG OBP Assistant

Cette mini-application permet de poser des questions sur la documentation OBP via une interface web simple et une base de connaissances locale.

## Fonctionnement

- Le script [fetch_doc_obp.py](fetch_doc_obp.py) télécharge la documentation OBP et génère un fichier JSON de connaissances.
- L’application web [app.py](app.py) sert une interface simple et répond à partir du fichier [datasets/obp_knowledge.json](datasets/obp_knowledge.json).
- Les tests Playwright dans [tests/assistant.spec.js](tests/assistant.spec.js) vérifient les scénarios principaux de l’interface.

## Prérequis

- Python 3.12+
- Node.js 20+

## Installation

```bash
python -m pip install requests
npm install
```

## Générer la base de connaissances

```bash
python fetch_doc_obp.py
```

## Lancer l’application

```bash
python app.py
```

Puis ouvrir : http://127.0.0.1:8000/

## Lancer les tests Playwright

```bash
npx playwright install chromium
npx playwright test
```
