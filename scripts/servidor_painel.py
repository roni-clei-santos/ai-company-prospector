#!/usr/bin/env python3
"""Local server of the panel, like a local app (Jupyter style): http://127.0.0.1:<port chosen by the system>.

Standard library only (http.server). One server per project. It serves the panel and records the
"Feito"/"Desfazer" clicks of the "Pendentes" tab through scripts/registrar.py, at once.

  GET  /                       -> the panel (scripts/painel_template.html, with this run's token)
  GET  /data.json              -> the panel data, built on every request (token)
  GET  /relatorios/<nome>.html -> a report pre-rendered in painel/relatorios/
  GET  /api/estado             -> {"ok", "versao", "pid"} (used by gerar_painel.py to reuse a running server)
  POST /api/estado             -> heartbeat of an open panel (every 30 s; token)
  POST /api/feito     {"id"}   -> records the item as ENVIADO today (idempotent), returns fresh data (token)
  POST /api/desfazer  {"id"}   -> reverts what /api/feito wrote (idempotent), returns fresh data (token)
  POST /api/fechou             -> the panel tab was closed (navigator.sendBeacon, token in the body)

Protection: binds to 127.0.0.1 only; the Host header must be 127.0.0.1:<port>; the only Origin accepted is
http://127.0.0.1:<port> (any other: 403); requests sent from another site (Sec-Fetch-Site cross-site) are
refused, except opening the page itself; every POST and /data.json need the token of this run, which only
exists inside the served page. Nothing is written to disk except controle/.painel-servidor.json
({pid, porta, iniciado_em}, gitignored), deleted when the server stops.

It stops by itself: 15 s after the last panel tab is closed (no new request in between, so reloading the
page keeps it), or 3 minutes without any heartbeat or request. No network call at start.

Usage (from any folder; on Windows use `py -3`):
  python3 scripts/servidor_painel.py           start in the foreground (Ctrl+C stops it)
  The usual way is /painel (python3 scripts/gerar_painel.py), which starts or reuses it and opens the panel.
"""
import argparse
import hmac
import json
import os
import secrets
import signal
import socketserver
import sys
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gerar_painel  # noqa: E402
import registrar  # noqa: E402
from common import NO_PROJECT, PANEL_STATE, find_project, panel_url, write_json_atomic  # noqa: E402
from relatorio_html import OUT_DIR as REPORTS_DIR, SAFE_NAME  # noqa: E402

TEMPLATE = Path(__file__).resolve().parent / "painel_template.html"
TOKEN_MARK = "__PAINEL_TOKEN__"
VERSION = 3
NO_HEARTBEAT_S = float(os.environ.get("PAINEL_SEM_BATIMENTO_S") or 180)  # tests shorten it
CLOSED_S = float(os.environ.get("PAINEL_FECHOU_S") or 15)
PAGE_ALIVE_S = 65  # a page that sent a heartbeat this recently is still open
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


class PanelServer(ThreadingHTTPServer):
    daemon_threads = True
    # On Windows SO_REUSEADDR lets a second program bind a port already in use: never set it there.
    allow_reuse_address = os.name != "nt"

    def server_bind(self):
        # HTTPServer.server_bind() calls socket.getfqdn(), a reverse DNS lookup of 127.0.0.1. On macOS that
        # goes through mDNS ("find devices on local networks") and can hold the start for a long time.
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]


def make_handler(root, token, today=None):
    root = Path(root)
    reports = root / REPORTS_DIR
    page = TEMPLATE.read_text(encoding="utf-8").replace(TOKEN_MARK, token).encode("utf-8")

    class Handler(BaseHTTPRequestHandler):
        server_version = "PainelLocal"
        timeout = 15  # an idle connection never holds a worker forever

        def log_message(self, *args):  # quiet
            pass

        # ---------- checks ----------
        def _own(self):
            return f"http://127.0.0.1:{self.server.server_address[1]}"

        def _host_ok(self):
            return self.headers.get("Host") == f"127.0.0.1:{self.server.server_address[1]}"

        def _origin_ok(self, required=False):
            origin = self.headers.get("Origin")
            return origin == self._own() if (required or origin is not None) else True

        def _token_ok(self, body=None):
            given = self.headers.get("X-Painel-Token") or ((body or {}).get("token") if isinstance(body, dict) else None) or ""
            return hmac.compare_digest(str(given).encode(), token.encode())

        def _same_page(self):
            site = self.headers.get("Sec-Fetch-Site")
            return not site or site in ("same-origin", "none")

        def _navigation(self):
            return self.headers.get("Sec-Fetch-Mode") == "navigate" and self.headers.get("Sec-Fetch-Dest") in (None, "document")

        # ---------- replies ----------
        def _send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
            raw = body if isinstance(body, bytes) else body.encode("utf-8")
            self.send_response(code)
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
            print(f"recusado: {self.command} {self.path.split('?', 1)[0]} Origin={self.headers.get('Origin')} "
                  f"Sec-Fetch-Site={self.headers.get('Sec-Fetch-Site')}", file=sys.stderr, flush=True)
            self._json(403, {"ok": False, "erro": "acesso só pelo próprio painel"})

        def _data(self):
            data = gerar_painel.build(root, today=today)
            gerar_painel.render_cited_reports(root, data)
            return data

        def _activity(self):
            self.server.last_activity = time.time()
            self.server.closing_at = None

        # ---------- GET ----------
        def do_GET(self):
            self._activity()
            if not self._host_ok() or not self._origin_ok():
                return self._deny()
            path = self.path.split("?", 1)[0].split("#", 1)[0]
            if path in ("/", "/index.html"):
                if not (self._same_page() or self._navigation()):
                    return self._deny()
                return self._send(200, page, "text/html; charset=utf-8")
            if path.startswith("/relatorios/"):
                if not (self._same_page() or self._navigation()):
                    return self._deny()
                return self._report(path[len("/relatorios/"):])
            if not self._same_page():
                return self._deny()
            if path == "/api/estado":
                return self._json(200, {"ok": True, "versao": VERSION, "pid": os.getpid()})
            if path == "/data.json":
                return self._json(200, self._data()) if self._token_ok() else self._deny()
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
            path = self.path.split("?", 1)[0]
            try:
                length = min(int(self.headers.get("Content-Length") or 0), 10_000)
                body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            except (ValueError, UnicodeDecodeError):
                body = None
            # every POST needs the token; the Origin, when sent, must be this server. Only the beacon of a closed
            # tab (/api/fechou) may come without Origin: some browsers (Firefox) do not send it on sendBeacon.
            if (not self._host_ok() or not self._origin_ok(required=path != "/api/fechou") or not self._same_page()
                    or not self._token_ok(body)):
                return self._deny()
            if not isinstance(body, dict):
                return self._json(400, {"ok": False, "erro": "pedido inválido"})
            page_id = str(body.get("pagina") or "")[:40]
            if path == "/api/fechou":
                with self.server.lock:
                    self.server.pages.pop(page_id, None)
                    now = time.time()
                    if not any(now - t < PAGE_ALIVE_S for t in self.server.pages.values()):
                        self.server.closing_at = now + CLOSED_S
                print(f"aba fechada ({page_id or 'sem id'}); desliga em {int(CLOSED_S)} s se nada mais chegar",
                      file=sys.stderr, flush=True)
                return self._json(200, {"ok": True})
            self._activity()
            if path == "/api/estado":
                if page_id:
                    with self.server.lock:
                        self.server.pages[page_id] = time.time()
                return self._json(200, {"ok": True})
            item_id = body.get("id")
            if not isinstance(item_id, str) or not item_id:
                return self._json(400, {"ok": False, "erro": "pedido inválido"})
            try:
                with self.server.lock:  # one write at a time
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
    """Server on 127.0.0.1 (port 0 = a free port chosen by the system) with a token for this run only."""
    token = token or secrets.token_urlsafe(24)
    server = PanelServer(("127.0.0.1", port), make_handler(root, token, today))
    server.token = token
    server.last_activity = time.time()
    server.closing_at = None
    server.pages = {}
    server.lock = threading.Lock()
    return server


def should_stop(server, now=None):
    now = now or time.time()
    if server.closing_at is not None and now >= server.closing_at:
        return "painel fechado"
    if now - server.last_activity > NO_HEARTBEAT_S:
        return f"{int(NO_HEARTBEAT_S)} s sem uso"
    return None


def serve(root):
    root = Path(root)
    url = panel_url(root)
    if url:
        print(f"O painel deste projeto já está aberto em {url}", flush=True)
        return
    server = make_server(root)
    port = server.server_address[1]
    state = root / PANEL_STATE
    state.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(state, {"pid": os.getpid(), "porta": port, "iniciado_em": datetime.now().isoformat(timespec="seconds")})
    print(f"Painel em http://127.0.0.1:{port}/ (só neste computador). Fecha sozinho quando a aba for fechada.", flush=True)
    stop = threading.Event()
    try:
        signal.signal(signal.SIGTERM, lambda *a: stop.set())
    except (ValueError, OSError, AttributeError):
        pass
    worker = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.5}, daemon=True)
    worker.start()
    reason = "interrompido"
    try:
        while not stop.wait(0.5):
            reason = should_stop(server)
            if reason:
                break
    except KeyboardInterrupt:
        reason = "Ctrl+C"
    finally:
        server.shutdown()
        server.server_close()
        try:
            if json.loads(state.read_text(encoding="utf-8")).get("pid") == os.getpid():
                state.unlink()
        except (OSError, ValueError):
            pass
        print(f"Painel encerrado ({reason or 'interrompido'}).", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Servidor local do painel (só 127.0.0.1).")
    ap.add_argument("--raiz", help="pasta do projeto (padrão: a busca de scripts/common.py)")
    args = ap.parse_args(argv)
    root = Path(args.raiz).resolve() if args.raiz else find_project()
    if root is None:
        print(NO_PROJECT)
        sys.exit(1)
    serve(root)


if __name__ == "__main__":
    main()
