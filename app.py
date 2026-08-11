import json
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "datasets" / "obp_knowledge.json"


class RAGHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/health":
            self._send_json({"status": "ok"})
            return

        if path in ("/", "/index.html"):
            self._serve_static("index.html", "text/html; charset=utf-8")
            return

        if path == "/styles.css":
            self._serve_static("styles.css", "text/css; charset=utf-8")
            return

        if path == "/app.js":
            self._serve_static("app.js", "application/javascript; charset=utf-8")
            return

        self._send_text("Not found", 404, "text/plain; charset=utf-8")

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/chat":
            self._send_text("Not found", 404, "text/plain; charset=utf-8")
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length).decode("utf-8")

        try:
            payload = json.loads(body or "{}")
        except json.JSONDecodeError:
            self._send_json({"error": "Le payload JSON est invalide."}, 400)
            return

        message = (payload.get("message") or "").strip()
        if not message:
            self._send_json({"error": "Veuillez saisir une question."}, 400)
            return

        try:
            time.sleep(0.8)
            answer = self._answer_from_knowledge(message)
            self._send_json(answer)
        except Exception as exc:  # pragma: no cover - defensive path
            self._send_json({"error": "Le service est indisponible pour le moment. Réessayez plus tard."}, 500)
            print(f"Server error: {exc}")

    def _answer_from_knowledge(self, question: str):
        documents = self._load_documents()
        if not documents:
            return {"error": "Aucune base de connaissances n'est disponible."}

        query_terms = set(re.findall(r"[a-zA-Z0-9_]+", question.lower()))
        if not query_terms:
            return {"answer": "Je n'ai pas assez d'éléments pour répondre. Veuillez reformuler votre question.", "source": "", "summary": ""}

        scored = []
        for doc in documents:
            content = f"{doc.get('summary', '')} {doc.get('content', '')} { ' '.join(doc.get('tags', [])) }".lower()
            matches = sum(1 for term in query_terms if term in content)
            if matches:
                scored.append((matches, doc))

        scored.sort(key=lambda item: item[0], reverse=True)
        if not scored:
            return {
                "answer": "Je n'ai pas trouvé de correspondance assez proche dans la base OBP. Essayez un terme comme compte, transaction, permission ou vue.",
                "source": "",
                "summary": "",
            }

        _, best_doc = scored[0]
        excerpt = best_doc.get("content", "").replace("\n", " ").strip()
        if len(excerpt) > 420:
            excerpt = excerpt[:420] + "..."

        return {
            "answer": f"Voici une réponse basée sur la base locale : {best_doc.get('summary', 'documentation OBP')}. {excerpt}",
            "source": best_doc.get("source", ""),
            "summary": best_doc.get("summary", ""),
        }

    def _load_documents(self):
        with DATASET_PATH.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _serve_static(self, file_name: str, content_type: str):
        path = ROOT / file_name
        if path.exists():
            self._send_file(path, content_type)
        else:
            self._send_text("Not found", 404, "text/plain; charset=utf-8")

    def _send_file(self, path: Path, content_type: str):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(path.stat().st_size))
        self.end_headers()
        with path.open("rb") as handle:
            self.wfile.write(handle.read())

    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, text, status, content_type):
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


def main():
    host = "0.0.0.0"
    port = int(__import__("os").getenv("PORT", "8000"))
    server = ThreadingHTTPServer((host, port), RAGHandler)
    print(f"Serveur démarré sur http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
