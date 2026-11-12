"""Tests for the local panel server and the "Feito" button (fictitious data only).

POST /api/feito records the item as ENVIADO today in every place the robot records a send
(progresso.json, relatorio-parcial.md, company report, draft file, historico-contatos.md and
relatorio-final.xlsx); POST /api/desfazer reverts exactly those writes. Runs on macOS, Linux and
Windows (standard library server on 127.0.0.1; the Chrome renders are skipped without Chrome).
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path

import openpyxl
import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "tests"))
import gerar_painel  # noqa: E402
import registrar  # noqa: E402
import servidor_painel  # noqa: E402
from test_gerar_painel import CHROME, NO_CHROME_REASON, SKIP_RENDER_REASON  # noqa: E402
from test_pendentes import TODAY, make_project  # noqa: E402

GERENTE = "li:linkedin.com/in/gerente-exemplo"
EMAIL3 = "em:3:socio@agencia3.example.com"
FOLLOWUP2 = "fu:2:2026-11-12"
REPORT1 = "relatorios/001-loja-exemplo-1.md"
CONTACTS = "controle/historico-contatos.md"


@pytest.fixture
def server(tmp_path, monkeypatch):
    make_project(tmp_path, monkeypatch)
    (tmp_path / REPORT1).write_text("# #1 Loja Exemplo 1\n\n- Status: RASCUNHOS_CRIADOS\n", encoding="utf-8")
    (tmp_path / CONTACTS).write_text("# Histórico de contatos\n\n## Por empresa\n\n### #1 Loja Exemplo 1 — checado em 2026-11-09\n"
                                     "- Nada antes.\n\n### #2 Agência Exemplo 2\n- Nada antes.\n", encoding="utf-8")
    wb = openpyxl.load_workbook(tmp_path / "relatorio-final.xlsx")
    ws = wb["Empresas"]
    ws.cell(row=1, column=7, value="Rascunhos criados")
    ws.cell(row=1, column=8, value="Pendências do candidato")
    ws.cell(row=2, column=7, value="LinkedIn: 1 nota de convite.")
    wb.save(tmp_path / "relatorio-final.xlsx")
    srv = servidor_painel.make_server(tmp_path, today=TODAY)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    srv.root = tmp_path
    srv.base = f"http://127.0.0.1:{srv.server_address[1]}"
    yield srv
    srv.shutdown()
    srv.server_close()


def call(srv, path, body=None, headers=None, token=True, origin=True):
    h = {"Content-Type": "application/json"}
    if body is not None:
        if token:
            h["X-Painel-Token"] = srv.token
        if origin:
            h["Origin"] = srv.base
    h.update(headers or {})
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(srv.base + path, data=data, headers=h, method="POST" if body is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")


def snapshot(root):
    files = ["relatorio-parcial.md", "rascunhos/linkedin/001-loja-exemplo-1.md", "rascunhos/email/003-agencia-exemplo-3.md",
             REPORT1, CONTACTS, "controle/progresso.json"]
    texts = {f: (root / f).read_text(encoding="utf-8") for f in files}
    texts["controle/progresso.json"] = json.loads(texts["controle/progresso.json"])  # same content, any formatting
    ws = openpyxl.load_workbook(root / "relatorio-final.xlsx")["Empresas"]
    texts["xlsx"] = [[c.value for c in row] for row in ws.iter_rows()]
    return texts


def test_serves_panel_with_persistent_token(server):
    code, js = call(server, "/data.js")
    assert code == 200 and js.startswith("window.PAINEL_DATA = ") and server.token not in js
    code, js = call(server, "/servidor.js")
    assert code == 200 and js == f'window.PAINEL_SERVIDOR = {{"url": "{server.base}", "token": "{server.token}"}};\n'
    assert (server.root / "controle" / ".painel-token").read_text(encoding="utf-8").strip() == server.token
    assert re.fullmatch(r"[0-9a-f]{64}", server.token)
    code, html = call(server, "/index.html")
    assert code == 200 and "Pendentes" in html
    assert call(server, "/api/estado")[0] == 403  # /api/* needs the token
    code, body = call(server, "/api/estado", headers={"X-Painel-Token": server.token})
    assert code == 200 and Path(json.loads(body)["raiz"]).resolve() == server.root.resolve()


def test_only_this_computer_and_this_page(server):
    assert call(server, "/data.js", headers={"Sec-Fetch-Site": "cross-site"})[0] == 403
    assert call(server, "/data.js", headers={"Sec-Fetch-Site": "cross-site", "Sec-Fetch-Mode": "navigate"})[0] == 403
    assert call(server, "/index.html", headers={"Sec-Fetch-Site": "cross-site", "Sec-Fetch-Mode": "navigate"})[0] == 200
    assert call(server, "/index.html", headers={"Sec-Fetch-Site": "cross-site", "Sec-Fetch-Mode": "no-cors"})[0] == 403
    assert call(server, "/data.json", headers={"Host": "evil.example.com"})[0] == 403
    assert call(server, "/servidor.js", headers={"Sec-Fetch-Site": "cross-site"})[0] == 403  # the token never leaks
    assert call(server, "/api/feito", {"id": GERENTE}, token=False)[0] == 403
    assert call(server, "/api/feito", {"id": GERENTE}, headers={"X-Painel-Token": "0" * 64})[0] == 403
    assert call(server, "/api/feito", {"id": GERENTE}, headers={"Origin": "https://example.com"})[0] == 403
    assert server.server_address[0] == "127.0.0.1"
    assert not (server.root / "controle" / "painel-feitos.json").exists()  # nothing was recorded


def test_feito_linkedin_records_everywhere_and_undo_reverts(server):
    root, before = server.root, snapshot(server.root)
    code, body = call(server, "/api/feito", {"id": GERENTE})
    assert code == 200, body
    out = json.loads(body)
    p = out["dados"]["pendentes"]
    assert GERENTE not in [it["id"] for it in p["linkedin"]]
    assert [s["id"] for s in p["enviados_hoje"]] == [GERENTE]
    assert p["enviados_hoje"][0]["descricao"] == "LinkedIn para Gerente Exemplo"
    c = p["conferencia"]
    assert c["linkedin_secao4"] == 6 and c["linkedin_secao4"] == c["linkedin_painel"] + c["ocultos_nao_contatar"]

    parcial = (root / "relatorio-parcial.md").read_text(encoding="utf-8")
    assert re.search(r"^\| ✅ \| 1 \| \*\*ENVIADO 12/11/2026\*\* Gerente Exemplo — ", parcial, re.M)
    draft = (root / "rascunhos/linkedin/001-loja-exemplo-1.md").read_text(encoding="utf-8")
    assert "## 1) [ENVIADO 12/11/2026] Gerente Exemplo — Gerente de E-commerce" in draft
    assert (root / REPORT1).read_text(encoding="utf-8").rstrip().endswith(
        "- ENVIADO 12/11/2026 (marcado no painel): LinkedIn para Gerente Exemplo.")
    contacts = (root / CONTACTS).read_text(encoding="utf-8")
    assert "- Nada antes.\n- (painel) 12/11/2026: ENVIADO pelo candidato, LinkedIn para Gerente Exemplo (#1 Loja Exemplo 1).\n\n### #2" in contacts
    prog = json.loads((root / "controle/progresso.json").read_text(encoding="utf-8"))
    assert prog["historico"][-1]["nota"] == "Painel: ENVIADO 12/11/2026 (marcado no painel): LinkedIn para Gerente Exemplo (#1)."
    ws = openpyxl.load_workbook(root / "relatorio-final.xlsx")["Empresas"]
    assert ws.cell(row=2, column=7).value == "LinkedIn: 1 nota de convite. | ENVIADO 12/11/2026 (marcado no painel): LinkedIn para Gerente Exemplo."
    assert registrar.done_ids(root) == {GERENTE}

    code, body = call(server, "/api/desfazer", {"id": GERENTE})
    assert code == 200 and json.loads(body)["avisos"] == []
    assert snapshot(root) == before
    p = json.loads(body)["dados"]["pendentes"]
    assert GERENTE in [it["id"] for it in p["linkedin"]] and p["enviados_hoje"] == []
    assert registrar.done_ids(root) == set()


def test_feito_email_followup_and_decision(server):
    root, before = server.root, snapshot(server.root)
    for item in (EMAIL3, FOLLOWUP2, "de:5"):
        code, body = call(server, "/api/feito", {"id": item})
        assert code == 200, body
    data = json.loads(body)["dados"]
    assert [s["id"] for s in data["pendentes"]["enviados_hoje"]] == [EMAIL3, FOLLOWUP2, "de:5"]
    assert EMAIL3 not in [e["id"] for e in data["pendentes"]["emails"]]
    assert FOLLOWUP2 not in [f["id"] for f in data["followups"]]
    assert [d["numero"] for d in data["pendentes"]["decisoes"]] == [4]
    parcial = (root / "relatorio-parcial.md").read_text(encoding="utf-8")
    assert "| 3 ✅ ENVIADO 12/11 | socio@agencia3.example.com |" in parcial
    assert (root / "rascunhos/email/003-agencia-exemplo-3.md").read_text(encoding="utf-8").startswith(
        "> ✅ ENVIADO pelo candidato em 12/11/2026 (marcado no painel).")
    # undo in any order: every file goes back to what it was
    for item in ("de:5", EMAIL3, FOLLOWUP2):
        assert call(server, "/api/desfazer", {"id": item})[0] == 200
    assert snapshot(root) == before


def test_feito_and_desfazer_are_idempotent(server):
    """A queued click may arrive twice, or for an item that is gone: 200, nothing written twice."""
    assert json.loads(call(server, "/api/feito", {"id": GERENTE})[1])["feito"] == GERENTE
    after_one = snapshot(server.root)
    code, body = call(server, "/api/feito", {"id": GERENTE})
    assert code == 200 and json.loads(body)["sem_mudanca"] is True
    assert snapshot(server.root) == after_one
    code, body = call(server, "/api/feito", {"id": "li:nao-existe"})
    assert code == 200 and json.loads(body)["ignorado"] == "item não está mais pendente"
    assert call(server, "/api/desfazer", {"id": GERENTE})[0] == 200
    before = snapshot(server.root)
    code, body = call(server, "/api/desfazer", {"id": GERENTE})
    assert code == 200 and json.loads(body)["sem_mudanca"] is True
    code, body = call(server, "/api/desfazer", {"id": "li:nao-existe"})
    assert code == 200 and json.loads(body)["sem_mudanca"] is True
    assert snapshot(server.root) == before
    assert registrar.done_ids(server.root) == set()


def _raw(srv, method, path, headers=None, body=None):
    """Request with the path sent exactly as given (urllib would normalize "../")."""
    import http.client
    conn = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=10)
    h = {"Host": f"127.0.0.1:{srv.server_address[1]}"}
    h.update(headers or {})
    conn.request(method, path, body=json.dumps(body) if body is not None else None, headers=h)
    r = conn.getresponse()
    out = (r.status, dict((k.lower(), v) for k, v in r.getheaders()), r.read().decode("utf-8", "replace"))
    conn.close()
    return out


def test_cors_for_the_page_opened_from_disk(server):
    """file:// pages send Origin "null": allowed with the token, never without it; other sites never."""
    code, h, _ = _raw(server, "OPTIONS", "/api/feito", {"Origin": "null", "Access-Control-Request-Method": "POST",
                                                        "Access-Control-Request-Headers": "content-type,x-painel-token"})
    assert code == 204
    assert h["access-control-allow-origin"] == "null"
    assert h["access-control-allow-methods"] == "GET, POST, OPTIONS"
    assert h["access-control-allow-headers"] == "Content-Type, X-Painel-Token"
    assert h["access-control-allow-private-network"] == "true" and h["access-control-max-age"] == "0"
    json_h = {"Origin": "null", "Content-Type": "application/json", "Sec-Fetch-Site": "cross-site"}
    code, h, body = _raw(server, "POST", "/api/feito", dict(json_h, **{"X-Painel-Token": server.token}), {"id": GERENTE})
    assert code == 200 and h["access-control-allow-origin"] == "null" and json.loads(body)["feito"] == GERENTE
    code, h, _ = _raw(server, "GET", "/data.json", {"Origin": "null", "Sec-Fetch-Site": "cross-site", "X-Painel-Token": server.token})
    assert code == 200 and h["access-control-allow-origin"] == "null"
    # wrong or missing token: refused, nothing written
    for headers in ({"X-Painel-Token": "f" * 64}, {}):
        code, h, _ = _raw(server, "POST", "/api/desfazer", dict(json_h, **headers), {"id": GERENTE})
        assert code == 403
        assert _raw(server, "GET", "/data.json", dict({"Origin": "null", "Sec-Fetch-Site": "cross-site"}, **headers))[0] == 403
    assert registrar.done_ids(server.root) == {GERENTE}
    # any other site: refused even with the token, and no CORS header for it
    for origin in ("https://example.com", "http://127.0.0.1:1"):
        code, h, _ = _raw(server, "OPTIONS", "/api/feito", {"Origin": origin, "Access-Control-Request-Method": "POST"})
        assert code == 403 and "access-control-allow-origin" not in h
        code, h, _ = _raw(server, "POST", "/api/desfazer", dict(json_h, Origin=origin, **{"X-Painel-Token": server.token}), {"id": GERENTE})
        assert code == 403 and "access-control-allow-origin" not in h
    assert registrar.done_ids(server.root) == {GERENTE}


def test_reports_only_from_painel_relatorios(server):
    reports = server.root / "painel" / "relatorios"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "001-loja-exemplo-1.html").write_text("<p>relatório</p>", encoding="utf-8")
    (server.root / "painel" / "segredo.html").write_text("segredo", encoding="utf-8")
    assert _raw(server, "GET", "/relatorios/001-loja-exemplo-1.html")[0] == 200
    for path in ("/relatorios/../segredo.html", "/relatorios/..%2fsegredo.html", "/relatorios/%2e%2e/segredo.html",
                 "/relatorios/../../controle/progresso.json", "/relatorios/..\\segredo.html", "/relatorios/Maiuscula.html",
                 "/relatorios/.oculto.html", "/relatorios/001-loja-exemplo-1.md", "/relatorios/nao-existe.html",
                 "/relatorios//etc/passwd", "/relatorios/sub/001-loja-exemplo-1.html"):
        code, _, body = _raw(server, "GET", path)
        assert code == 404 and "segredo" not in body and "empresas" not in body, path


def test_marked_item_never_comes_back(server):
    """A later check (or a new panel build) never "unmarks" what the candidate marked."""
    call(server, "/api/feito", {"id": FOLLOWUP2})
    data = gerar_painel.build(server.root, today=TODAY)
    assert FOLLOWUP2 not in [f["id"] for f in data["followups"]]
    assert [s["id"] for s in data["pendentes"]["enviados_hoje"]] == [FOLLOWUP2]
    assert gerar_painel.build(server.root, today="2026-11-13")["pendentes"]["enviados_hoje"] == []  # only today's


def test_opens_the_file_with_the_server_on(tmp_path, monkeypatch):
    """/painel opens painel/index.html (the same page as a double click) after starting the server."""
    make_project(tmp_path, monkeypatch)
    in_browser, fallback, started = [], [], []
    monkeypatch.setattr(gerar_painel, "open_file_in_browser", lambda uri: in_browser.append(uri) or True)
    monkeypatch.setattr(gerar_painel.webbrowser, "open", lambda uri: fallback.append(uri) or True)
    monkeypatch.setattr(gerar_painel, "ensure_server", lambda root: started.append(root) or "http://127.0.0.1:47321/index.html")
    gerar_painel.main([])
    gerar_painel.main(["--arquivo"])
    assert len(started) == 1 and fallback == []
    assert all(u.startswith("file://") and u.endswith("/painel/index.html") for u in in_browser) and len(in_browser) == 2
    assert (tmp_path / "painel" / "servidor.js").read_text(encoding="utf-8").startswith('window.PAINEL_SERVIDOR = {"url": "http://127.0.0.1:47321"')
    # no browser for file:// pages (unknown default browser): the server address is opened instead
    monkeypatch.setattr(gerar_painel, "open_file_in_browser", lambda uri: False)
    gerar_painel.main([])
    assert fallback == ["http://127.0.0.1:47321/index.html"]


def test_ensure_server_starts_and_reuses(tmp_path, monkeypatch):
    make_project(tmp_path, monkeypatch)
    url = gerar_painel.ensure_server(tmp_path)
    try:
        log = tmp_path / "controle" / ".painel-servidor.log"
        assert url and re.match(r"^http://127\.0\.0\.1:473(2\d|30)/index\.html$", url), log.read_text(errors="replace") if log.exists() else "sem log"
        assert gerar_painel.ensure_server(tmp_path) == url  # reused, not a second server
        token = (tmp_path / "controle" / ".painel-token").read_text(encoding="utf-8").strip()
        req = urllib.request.Request(url.replace("index.html", "api/estado"), headers={"X-Painel-Token": token})
        with urllib.request.urlopen(req, timeout=5) as r:
            assert Path(json.loads(r.read().decode("utf-8"))["raiz"]).resolve() == tmp_path.resolve()
        port = url.split(":")[2].split("/")[0]
        assert f'"url": "http://127.0.0.1:{port}", "token": "{token}"' in (tmp_path / "painel" / "servidor.js").read_text(encoding="utf-8")
    finally:
        _stop_detached(tmp_path)


def _stop_detached(root):
    path = root / "controle" / ".painel-servidor.json"
    if not path.exists():
        return
    state = json.loads(path.read_text(encoding="utf-8"))
    port = state["porta"]
    if sys.platform == "win32":
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        f"Get-NetTCPConnection -LocalPort {port} -State Listen | ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force }}"],
                       capture_output=True)
    else:
        subprocess.run(["pkill", "-f", f"servidor_painel.py --raiz {root}"], capture_output=True)
    (root / "controle" / ".painel-servidor.json").unlink(missing_ok=True)


def _dump(url):
    if not CHROME:
        pytest.skip(NO_CHROME_REASON)
    import os
    profile = tempfile.mkdtemp(prefix="chrome-test-")
    try:
        out = subprocess.run([CHROME, "--headless=new", "--disable-gpu", f"--user-data-dir={profile}", "--no-first-run",
                              "--no-default-browser-check", "--virtual-time-budget=3000", "--dump-dom", url],
                              capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30).stdout
        return re.sub(r"<script\b.*?</script>", "", out, flags=re.S)  # only the rendered page, not the JS source
    except subprocess.TimeoutExpired:
        if os.environ.get("CI") == "true" and sys.platform == "darwin":
            pytest.skip(SKIP_RENDER_REASON)
        raise
    finally:
        shutil.rmtree(profile, ignore_errors=True)


def test_render_through_server(server):
    html = _dump(server.base + "/index.html")
    sec = re.search(r'<section id="pendentes".*?</section>', html, re.S).group(0)
    assert "Enviados hoje" in sec and " disabled" not in sec and sec.count('data-done="') == 13


def test_render_from_file_feito_enabled(tmp_path, monkeypatch):
    """Opened straight from disk, even with no server: every "Feito" works (the click is queued)."""
    make_project(tmp_path, monkeypatch)
    html = _dump((tmp_path / "painel" / "index.html").as_uri())
    sec = re.search(r'<section id="pendentes".*?</section>', html, re.S).group(0)
    assert sec.count('data-done="') == 13 and " disabled" not in sec
    assert "Abra pelo /painel" not in sec and "Enviados hoje" in sec


def test_render_demo_only_strikes(tmp_path):
    """GitHub Pages has no server: the demo is served over http here too (file:// cannot fetch the JSON)."""
    import functools
    import http.server
    shutil.copytree(REPO / "docs" / "demo", tmp_path / "demo")
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(tmp_path / "demo"))
    handler.log_message = lambda *a: None
    httpd = http.server.HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        html = _dump(f"http://127.0.0.1:{httpd.server_address[1]}/index.html")
    finally:
        httpd.shutdown()
        httpd.server_close()
    sec = re.search(r'<section id="pendentes".*?</section>', html, re.S).group(0)
    assert 'Demonstração: o "Feito" só risca o item na tela.' in sec
    assert sec.count('data-done="') == 15 and " disabled" not in sec and "Enviados hoje" not in sec


def test_footer_author_links():
    for path in (REPO / "painel" / "index.html", REPO / "docs" / "demo" / "index.html"):
        html = path.read_text(encoding="utf-8")
        foot = re.search(r"<footer>.*?</footer>", html, re.S).group(0)
        assert "Feito por Roni Clei Santos" in foot
        assert 'href="https://www.linkedin.com/in/roni-clei-santos/" target="_blank" rel="noopener">LinkedIn</a>' in foot
        assert 'href="https://github.com/roni-clei-santos/ai-company-prospector" target="_blank" rel="noopener">GitHub</a>' in foot
        assert 'href="https://github.com/roni-clei-santos/ai-company-prospector" target="_blank" rel="noopener">Dar uma estrela no projeto</a>' in foot
