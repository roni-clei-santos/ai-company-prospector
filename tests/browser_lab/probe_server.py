#!/usr/bin/env python3
"""Probe server of the browser lab (standard library only). Listens on 127.0.0.1 only.

  OPTIONS *        -> 204 with the CORS / Private Network headers (Origin echoed, "null" included)
  POST /feito      -> 200 {"ok": true} with the right X-Painel-Token (read from probe/config.js), else 403
  GET  /probe/...  -> files of tests/browser_lab/probe/
  GET  /painel/... -> files of --painel <folder> (optional)

Every request is appended to <log> (results/server-log.json).
Usage: python tests/browser_lab/probe_server.py [port] [--log results/server-log.json] [--painel <folder>]
"""
import argparse
import json
import mimetypes
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE / "probe"
CONFIG = PROBE / "config.js"


def read_token(config=CONFIG):
    """Token of window.LAB in probe/config.js (written by run_lab.py before each test)."""
    try:
        m = re.search(r'"token"\s*:\s*"([^"]+)"', config.read_text(encoding="utf-8"))
        return m.group(1) if m else None
    except OSError:
        return None


def make_server(port=47321, log_path=Path("results/server-log.json"), painel_dir=None, config=CONFIG):
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        server_version = "BrowserLabProbe"

        def log_message(self, *args):
            pass

        def _record(self, status, body=""):
            h = self.headers
            entry = {
                "t": round(time.time(), 3),
                "metodo": self.command,
                "caminho": self.path,
                "status": status,
                "origin": h.get("Origin"),
                "ac_request_method": h.get("Access-Control-Request-Method"),
                "ac_request_headers": h.get("Access-Control-Request-Headers"),
                "ac_request_private_network": h.get("Access-Control-Request-Private-Network"),
                "sec_fetch_site": h.get("Sec-Fetch-Site"),
                "user_agent": h.get("User-Agent"),
                "corpo": body,
            }
            with lock:
                entries.append(entry)
                log_path.write_text(json.dumps(entries, ensure_ascii=False, indent=1), encoding="utf-8")

        def _cors(self):
            origin = self.headers.get("Origin")
            if origin is not None:  # "null" (file://) included
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")

        def _send(self, code, raw, ctype):
            self.send_response(code)
            self._cors()
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(raw)

        def do_OPTIONS(self):
            self._record(204)
            self.send_response(204)
            self._cors()
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Painel-Token")
            self.send_header("Access-Control-Allow-Private-Network", "true")
            self.send_header("Access-Control-Max-Age", "0")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_POST(self):
            length = min(int(self.headers.get("Content-Length") or 0), 10_000)
            body = self.rfile.read(length).decode("utf-8", "replace")
            if self.path.split("?", 1)[0] != "/feito":
                self._record(404, body)
                return self._send(404, b'{"ok":false}', "application/json")
            if self.headers.get("X-Painel-Token") != read_token(config):
                self._record(403, body)
                return self._send(403, b'{"ok":false,"erro":"token"}', "application/json")
            self._record(200, body)
            return self._send(200, b'{"ok":true}', "application/json")

        def do_GET(self):
            path = self.path.split("?", 1)[0].split("#", 1)[0]
            base, rel = None, None
            if path.startswith("/probe/"):
                base, rel = PROBE, path[len("/probe/"):]
            elif painel_dir and path.startswith("/painel/"):
                base, rel = Path(painel_dir), path[len("/painel/"):]
            target = (base / rel).resolve() if base else None
            if target is None or not target.is_file() or base.resolve() not in target.parents:
                self._record(404)
                return self._send(404, b"not found", "text/plain")
            self._record(200)
            ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            if ctype.startswith("text/") or ctype.endswith("javascript"):
                ctype += "; charset=utf-8"
            return self._send(200, target.read_bytes(), ctype)

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.entries = entries
    server.lock = lock
    return server


def main(argv=None):
    ap = argparse.ArgumentParser(description="Servidor de sonda do laboratório de navegadores (só 127.0.0.1).")
    ap.add_argument("port", nargs="?", type=int, default=47321)
    ap.add_argument("--log", default="results/server-log.json")
    ap.add_argument("--painel", help="pasta servida em /painel/")
    args = ap.parse_args(argv)
    server = make_server(args.port, args.log, args.painel)
    print(f"Sonda em http://127.0.0.1:{args.port}/probe/index.html", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
