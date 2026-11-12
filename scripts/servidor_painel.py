#!/usr/bin/env python3
"""Local server of the panel: http://127.0.0.1:<free port>, reachable only from this computer.

Standard library only (http.server). It serves painel/index.html with fresh data and records the
"Feito" clicks of the "Pendentes" tab through scripts/registrar.py (mark_done / undo_done).

  GET  /                  -> redirect to /index.html
  GET  /index.html        -> the panel
  GET  /data.js           -> window.PAINEL_DATA (rebuilt on every request) + window.PAINEL_SERVIDOR
  GET  /data.json         -> the same data as JSON
  GET  /api/estado        -> {"ok": true, "raiz": <project folder>} (used to reuse a running server)
  POST /api/feito         {"id": "<item id>"} -> records the item as ENVIADO today, returns fresh data
  POST /api/desfazer      {"id": "<item id>"} -> reverts what /api/feito wrote, returns fresh data

Protection: binds to 127.0.0.1 only; the Host header must be 127.0.0.1/localhost:<port>; requests
sent from another site (Sec-Fetch-Site cross-site) are refused; a POST needs the session token
(header X-Painel-Token) and the panel's own Origin. The server stops by itself after
--max-ocioso hours without requests (default 12).

Usage (from the project folder; on Windows use `py -3`):
  python3 scripts/servidor_painel.py              start in the foreground (Ctrl+C stops it)
  The usual way is `python3 scripts/gerar_painel.py`, which starts it in the background and opens it.
"""
import argparse
import json
import secrets
import sys
import time
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gerar_painel  # noqa: E402
import registrar  # noqa: E402
from common import project_root, write_json_atomic  # noqa: E402

STATE = Path("controle") / ".painel-servidor.json"
KINDS = (("linkedin", "linkedin"), ("emails", "email"), ("decisoes", "decisao"), ("respostas", "resposta"))


def find_item(data, item_id):
    """(kind, item) of a pending item of the panel data, or (None, None)."""
    p = data.get("pendentes") or {}
    for key, kind in KINDS:
        for it in p.get(key, []):
            if it.get("id") == item_id:
                return kind, it
    for f in data.get("followups", []):
        if f.get("id") == item_id:
            return "followup", f
    return None, None


def make_handler(root, token, today=None):
    root = Path(root)
    index_html = root / "painel" / "index.html"
    if not index_html.exists():
        index_html = Path(__file__).resolve().parent.parent / "painel" / "index.html"

    class Handler(BaseHTTPRequestHandler):
        server_version = "PainelLocal"

        def log_message(self, *args):  # quiet
            pass

        # ---------- helpers ----------
        def _origin(self):
            return f"http://{self.headers.get('Host', '')}"

        def _allowed(self):
            port = self.server.server_address[1]
            if self.headers.get("Host") not in (f"127.0.0.1:{port}", f"localhost:{port}"):
                return False
            site = self.headers.get("Sec-Fetch-Site")
            if not site or site in ("same-origin", "none"):
                return True
            # opening the page itself from a link or another tab is fine: it carries no data;
            # the data (data.js, data.json) and the API only answer the panel's own page
            return (self.command == "GET" and self.headers.get("Sec-Fetch-Mode") == "navigate"
                    and self.path.split("?", 1)[0] in ("/", "/index.html"))

        def _send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
            raw = body if isinstance(body, bytes) else body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(raw)

        def _json(self, code, obj):
            self._send(code, json.dumps(obj, ensure_ascii=False))

        def _data(self):
            return gerar_painel.build(root, today=today)

        # ---------- GET ----------
        def do_GET(self):
            self.server.last_request = time.time()
            if not self._allowed():
                return self._json(403, {"ok": False, "erro": "acesso só pelo próprio painel"})
            path = self.path.split("?", 1)[0]
            if path == "/":
                return self._send(302, b"", "text/plain", {"Location": "/index.html"})
            if path == "/index.html":
                return self._send(200, index_html.read_bytes(), "text/html; charset=utf-8")
            if path == "/data.js":
                payload = json.dumps(self._data(), ensure_ascii=False)
                js = f"window.PAINEL_DATA = {payload};\nwindow.PAINEL_SERVIDOR = {json.dumps({'token': token})};\n"
                return self._send(200, js, "text/javascript; charset=utf-8")
            if path == "/data.json":
                return self._json(200, self._data())
            if path == "/api/estado":
                return self._json(200, {"ok": True, "raiz": str(root)})
            return self._json(404, {"ok": False, "erro": "não encontrado"})

        # ---------- POST ----------
        def do_POST(self):
            self.server.last_request = time.time()
            port = self.server.server_address[1]
            origin = self.headers.get("Origin")
            if (not self._allowed() or self.headers.get("X-Painel-Token") != token
                    or origin not in (f"http://127.0.0.1:{port}", f"http://localhost:{port}")):
                return self._json(403, {"ok": False, "erro": "acesso só pelo próprio painel"})
            try:
                length = min(int(self.headers.get("Content-Length") or 0), 10_000)
                item_id = json.loads(self.rfile.read(length).decode("utf-8")).get("id")
            except (ValueError, AttributeError):
                return self._json(400, {"ok": False, "erro": "pedido inválido"})
            path = self.path.split("?", 1)[0]
            try:
                if path == "/api/feito":
                    kind, item = find_item(self._data(), item_id)
                    if item is None:
                        return self._json(404, {"ok": False, "erro": "item não está mais pendente"})
                    entry = registrar.mark_done(root, kind, item, today=today)
                    return self._json(200, {"ok": True, "feito": entry["id"], "dados": self._data()})
                if path == "/api/desfazer":
                    warnings = registrar.undo_done(root, item_id)
                    return self._json(200, {"ok": True, "avisos": warnings, "dados": self._data()})
            except (KeyError, ValueError) as e:
                return self._json(409, {"ok": False, "erro": str(e)})
            except Exception as e:  # noqa: BLE001 - report it on the page instead of a broken connection
                return self._json(500, {"ok": False, "erro": f"{type(e).__name__}: {e}"})
            return self._json(404, {"ok": False, "erro": "não encontrado"})

    return Handler


def make_server(root, port=0, token=None, today=None):
    token = token or secrets.token_urlsafe(24)
    server = HTTPServer(("127.0.0.1", port), make_handler(root, token, today))
    server.last_request = time.time()
    server.token = token
    return server


def serve(root, port=0, max_idle_hours=12.0):
    root = Path(root)
    server = make_server(root, port)
    port = server.server_address[1]
    state = root / STATE
    state.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(state, {"porta": port, "url": f"http://127.0.0.1:{port}/index.html", "raiz": str(root),
                              "iniciado_em": date.today().isoformat()})
    print(f"Painel em http://127.0.0.1:{port}/index.html (só neste computador). Ctrl+C para parar.", flush=True)
    server.timeout = 30
    try:
        while time.time() - server.last_request < max_idle_hours * 3600:
            server.handle_request()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        try:
            if json.loads(state.read_text(encoding="utf-8")).get("porta") == port:
                state.unlink()
        except (OSError, ValueError):
            pass


def main(argv=None):
    ap = argparse.ArgumentParser(description="Servidor local do painel (só 127.0.0.1).")
    ap.add_argument("--raiz", help="pasta do projeto (padrão: a pasta atual ou $PROSPECT_DIR)")
    ap.add_argument("--porta", type=int, default=0, help="porta (padrão: uma porta livre)")
    ap.add_argument("--max-ocioso", type=float, default=12.0, help="horas sem uso até parar sozinho")
    args = ap.parse_args(argv)
    serve(Path(args.raiz).resolve() if args.raiz else project_root(), args.porta, args.max_ocioso)


if __name__ == "__main__":
    main()
