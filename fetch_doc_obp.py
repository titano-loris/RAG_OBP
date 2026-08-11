# Récupère la documentation OBP et la transforme en base de connaissances RAG.

import json
import re 
# pathlib permet de construire des chemins plus simple
from pathlib import Path 
import requests

OBP_RESOURCE_DOCS = (
    "https://apisandbox.openbankproject.com/obp/v6.0.0/resource-docs/v6.0.0/obp"
)
# choix des tags pour faire le tri eds 884 endpoints
TAGS_RETENUS = {"Account", "Transaction", "Account-Access-Request"}
# Avec pathlib :  racine / "datasets" / "obp_knowledge.json"
# sans pathlib :  racine + "\\" + "datasets" + "\\" + "obp_knowledge.json" 
OUTPUT_PATH = Path(__file__).parent / "datasets" / "obp_knowledge.json"

# regex pour retirer les balises HTML résiduelles et normaliser les espaces
def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-z]+;|&#\d+;", " ", text)  # entités HTML
    return re.sub(r"\s+", " ", text).strip()

# Transforme un endpoint de la doc OBP en document RAG.
# "(endpoint: dict) -> dict" retourne un dictionnaire
def build_document(endpoint: dict) -> dict: 
# description_markdown le texte sans les balise html
    description = endpoint.get("description_markdown") or ""
# si champs vide trouver description (la version HTML) et nmettre au propre avec regex strip_html
    if not description:
        description = strip_html(endpoint.get("description", ""))
# details de la variable roles: [  EXPRESSION  for ÉLÉMENT in ITÉRABLE  if CONDITION  ] afin de selectioner des élements de l'objet
    roles = [r.get("role", "") for r in endpoint.get("roles", []) if r.get("role")]
    errors = endpoint.get("error_response_bodies", [])

 # Le contenu que le RAG va indexer : tout ce qui aide à répondre
    parts = [
        f"Endpoint : {endpoint.get('summary', '')}",
        f"Méthode : {endpoint.get('request_verb', '')} {endpoint.get('request_url', '')}",
        f"Description : {description}",
    ]

    if roles:
        parts.append(f"Rôles requis : {', '.join(roles)}")
    if errors:
        parts.append(f"Erreurs possibles : {' | '.join(errors[:5])}")
# le contenu JSON
    return {
            "id": endpoint.get("operation_id", ""),
            "source": endpoint.get("request_url", ""),
            "summary": endpoint.get("summary", ""),
            "verb": endpoint.get("request_verb", ""),
            "tags": endpoint.get("tags", []),
            "roles": roles,
            "content": "\n".join(parts),
    }

def main():
    print(f"Téléchargement de la doc OBP...\n  {OBP_RESOURCE_DOCS}")
    response = requests.get(OBP_RESOURCE_DOCS, timeout=120)
    response.raise_for_status()

    all_endpoints = response.json().get("resource_docs", [])
    print(f"  {len(all_endpoints)} endpoints reçus au total")

    # Filtrage sur les tags du périmètre MVP
    selected = [
        ep for ep in all_endpoints
        if TAGS_RETENUS & set(ep.get("tags", []))
    ]
    print(f"  {len(selected)} endpoints retenus (tags : {', '.join(sorted(TAGS_RETENUS))})")

    documents = [build_document(ep) for ep in selected]
    documents = [d for d in documents if len(d["content"]) > 100]  # écarte les vides

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(documents, f, ensure_ascii=False, indent=2)

    print(f"\n✅ {len(documents)} documents écrits dans {OUTPUT_PATH}")
    print("\nAperçu du premier document :")
    print(documents[0]["content"][:400] + "...")


if __name__ == "__main__":
    main()