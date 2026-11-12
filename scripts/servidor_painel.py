#!/usr/bin/env python3
"""Local server of the panel: http://127.0.0.1:47321 (47322..47330 if taken), only on this computer.

Standard library only (http.server). It records the "Feito" clicks of the "Pendentes" tab through
scripts/registrar.py (mark_done / undo_done), for the panel opened from the server AND for the panel
opened straight from disk (file://, Origin "null"), which reaches it through CORS.

  GET  /, /index.html          -> the panel
  GET  /servidor.js            -> window.PAINEL_SERVIDOR = {url, token}   (same page only)
  GET  /data.js                -> window.PAINEL_DATA (rebuilt on every request)  (same page only)
  GET  /data.json              -> the same data as JSON (same page, or any accepted Origin with the token)
  GET  /relatorios/<nome>.html -> a report pre-rendered in painel/relatorios/
  GET  /api/estado             -> {"ok", "raiz", "porta", "versao"} (token; keeps the server alive)
  POST /api/feito     {"id"}   -> records the item as ENVIADO today (idempotent), returns fresh data
  POST /api/desfazer  {"id"}   -> reverts what /api/feito wrote (idempotent), returns fresh data
  OPTIONS *                    -> CORS preflight

Protection: binds to 127.0.0.1 only; the Host header must be 127.0.0.1/localhost:<port>; the only
Origins accepted are "null" (file:// pages), http://127.0.0.1:<port> and http://localhost:<port>;
every /api/* call needs the token (header X-Painel-Token). The token is 32 random bytes kept in
controle/.painel-token and painel/servidor.js (both local and gitignored), so a site on the internet
(even a sandboxed iframe, which also sends Origin "null") cannot read or write anything.
The server stops by itself 30 minutes after the last request; an open panel pings it every 60 s.

Usage (from any folder; on Windows use `py -3`):
  python3 scripts/servidor_painel.py           start in the foreground (Ctrl+C stops it)
  The usual way is `python3 scripts/gerar_painel.py`, which starts it in the background and opens the panel.
"""
import argparse
import hmac
import json
import os
import re
import sys
import time
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gerar_painel  # noqa: E402
import registrar  # noqa: E402
from common import (NO_PROJECT, PANEL_PORTS, find_project, painel_token, server_js,  # noqa: E402
                    write_json_atomic, write_server_js)
from relatorio_html import OUT_DIR as REPORTS_DIR, SAFE_NAME  # noqa: E402

STATE = Path("controle") / ".painel-servidor.json"
VERSION = 2
IDLE_MINUTES = 30.0
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


class PanelServer(HTTPServer):
    # On Windows SO_REUSEADDR lets a second program bind a port already in use: never set it there.
    allow_reuse_address = os.name != "nt"


def make_handler(root, token, today=None):
    root = Path(root)
    index_html = root / "painel" / "index.html"
    if not index_html.exists():
        index_html = Path(__file__).resolve().parent.parent / "painel" / "index.html"
    reports = root / REPORTS_DIR

    class Handler(BaseHTTPRequestHandler):
        server_version = "PainelLocal"

        def log_message(self, *args):  # quiet
            pass

        # ---------- checks ----------
        def _port(self):
            return self.server.server_address[1]

        def _own(self):
            return (f"http://127.0.0.1:{self._port()}", f"http://localhost:{self._port()}")

        def _host_ok(self):
            return self.headers.get("Host") in (f"127.0.0.1:{self._port()}", f"localhost:{self._port()}")

        def _origin_ok(self):
            origin = self.headers.get("Origin")
            return origin is None or origin == "null" or origin in self._own()

        def _token_ok(self):
            return hmac.compare_digest((self.headers.get("X-Painel-Token") or "").encode(), token.encode())

        def _same_page(self):
            site = self.headers.get("Sec-Fetch-Site")
            return not site or site in ("same-origin", "none")

        def _navigation(self):
            return self.headers.get("Sec-Fetch-Mode") == "navigate" and self.headers.get("Sec-Fetch-Dest") in (None, "document")

        # ---------- replies ----------
        def _cors(self):
            origin = self.headers.get("Origin")
            if origin is not None and (origin == "null" or origin in self._own()):
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")

        def _send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
            raw = body if isinstance(body, bytes) else body.encode("utf-8")
            self.send_response(code)
            self._cors()
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            if ctype.startswith("text/html"):
                self.send_header("X-Frame-Options", "DENY")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(raw)

        def _json(self, code, obj):
            self._send(code, json.dumps(obj, ensure_ascii=False))

        def _deny(self):
            self._json(403, {"ok": False, "erro": "acesso só pelo próprio painel"})

        def _data(self):
            data = gerar_painel.build(root, today=today)
            gerar_painel.render_cited_reports(root, data)
            return data

        # ---------- OPTIONS (CORS preflight) ----------
        def do_OPTIONS(self):
            self.server.last_request = time.time()
            if not self._host_ok() or self.headers.get("Origin") is None or not self._origin_ok():
                return self._deny()
            self.send_response(204)
            self._cors()
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Painel-Token")
            self.send_header("Access-Control-Allow-Private-Network", "true")
            self.send_header("Access-Control-Max-Age", "0")
            self.send_header("Content-Length", "0")
            self.end_headers()

        # ---------- GET ----------
        def do_GET(self):
            self.server.last_request = time.time()
            if not self._host_ok() or not self._origin_ok():
                return self._deny()
            path = self.path.split("?", 1)[0].split("#", 1)[0]
            if path.startswith("/api/"):
                if not self._token_ok():
                    return self._deny()
                if path == "/api/estado":
                    return self._json(200, {"ok": True, "raiz": str(root), "porta": self._port(), "versao": VERSION})
                return self._json(404, {"ok": False, "erro": "não encontrado"})
            if path in ("/", "/index.html"):
                if not (self._same_page() or self._navigation()):
                    return self._deny()
                if path == "/":
                    return self._send(302, b"", "text/plain", {"Location": "/index.html"})
                return self._send(200, index_html.read_bytes(), "text/html; charset=utf-8")
            if path.startswith("/relatorios/"):
                if not (self._same_page() or self._navigation()):
                    return self._deny()
                return self._report(path[len("/relatorios/"):])
            if path == "/data.json":
                if not (self._same_page() or self._token_ok()):
                    return self._deny()
                return self._json(200, self._data())
            if path in ("/servidor.js", "/data.js"):
                if not self._same_page():
                    return self._deny()
                if path == "/servidor.js":
                    return self._send(200, server_js(self._port(), token), "text/javascript; charset=utf-8")
                payload = json.dumps(self._data(), ensure_ascii=False)
                return self._send(200, f"window.PAINEL_DATA = {payload};\n", "text/javascript; charset=utf-8")
            return self._json(404, {"ok": False, "erro": "não encontrado"})

        do_HEAD = do_GET

        def _report(self, name):
            if not SAFE_NAME.match(name):
                return self._json(404, {"ok": False, "erro": "não encontrado"})
            base = reports.resolve()
            target = (reports / name).resolve()
            if target.parent != base or not target.is_file():
                return self._json(404, {"ok": False, "erro": "não encontrado"})
            return self._send(200, target.read_bytes(), "text/html; charset=utf-8")

        # ---------- POST ----------
        def do_POST(self):
            self.server.last_request = time.time()
            if not self._host_ok() or not self._origin_ok() or not self._token_ok():
                return self._deny()
            try:
                length = min(int(self.headers.get("Content-Length") or 0), 10_000)
                item_id = json.loads(self.rfile.read(length).decode("utf-8")).get("id")
                if not isinstance(item_id, str) or not item_id:
                    raise ValueError("id")
            except (ValueError, AttributeError):
                return self._json(400, {"ok": False, "erro": "pedido inválido"})
            path = self.path.split("?", 1)[0]
            try:
                if path == "/api/feito":
                    if item_id in registrar.done_ids(root):
                        return self._json(200, {"ok": True, "sem_mudanca": True, "dados": self._data()})
                    kind, item = find_item(gerar_painel.build(root, today=today), item_id)
                    if item is None:
                        return self._json(200, {"ok": True, "ignorado": "item não está mais pendente", "dados": self._data()})
                    entry = registrar.mark_done(root, kind, item, today=today)
                    return self._json(200, {"ok": True, "feito": entry["id"], "dados": self._data()})
                if path == "/api/desfazer":
                    if item_id not in registrar.done_ids(root):
                        return self._json(200, {"ok": True, "sem_mudanca": True, "dados": self._data()})
                    warnings = registrar.undo_done(root, item_id)
                    return self._json(200, {"ok": True, "avisos": warnings, "dados": self._data()})
            except (KeyError, ValueError) as e:
                return self._json(409, {"ok": False, "erro": str(e)})
            except Exception as e:  # noqa: BLE001 - report it on the page instead of a broken connection
                return self._json(500, {"ok": False, "erro": f"{type(e).__name__}: {e}"})
            return self._json(404, {"ok": False, "erro": "não encontrado"})

    return Handler


def make_server(root, port=0, token=None, today=None):
    token = token or painel_token(root)
    server = PanelServer(("127.0.0.1", port), make_handler(root, token, today))
    server.last_request = time.time()
    server.token = token
    return server


def bind(root, ports=PANEL_PORTS, today=None):
    """Server on the first free port of `ports` (47321, then 47322..47330)."""
    last = None
    for port in ports:
        try:
            return make_server(root, port, today=today)
        except OSError as e:
            last = e
    raise OSError(f"portas {ports[0]} a {ports[-1]} ocupadas ({last})")


def serve(root, ports=PANEL_PORTS, max_idle_minutes=IDLE_MINUTES):
    root = Path(root)
    server = bind(root, ports)
    port = server.server_address[1]
    write_server_js(root, port, server.token)
    state = root / STATE
    state.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(state, {"porta": port, "url": f"http://127.0.0.1:{port}/index.html", "raiz": str(root),
                              "iniciado_em": date.today().isoformat(), "versao": VERSION})
    print(f"Painel em http://127.0.0.1:{port}/index.html (só neste computador). Ctrl+C para parar.", flush=True)
    server.timeout = 30
    try:
        while time.time() - server.last_request < max_idle_minutes * 60:
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
    ap.add_argument("--raiz", help="pasta do projeto (padrão: a busca de scripts/common.py > project_root)")
    ap.add_argument("--porta", type=int, help="uma porta só (padrão: 47321, depois 47322 a 47330)")
    ap.add_argument("--max-ocioso", type=float, default=IDLE_MINUTES, help="minutos sem uso até parar sozinho")
    args = ap.parse_args(argv)
    root = Path(args.raiz).resolve() if args.raiz else find_project()
    if root is None:
        print(NO_PROJECT)
        sys.exit(1)
    serve(root, [args.porta] if args.porta else PANEL_PORTS, args.max_ocioso)


if __name__ == "__main__":
    main()
