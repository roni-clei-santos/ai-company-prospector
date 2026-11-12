"""Tests for the local panel server and the "Feito" button (fictitious data only).

Every test starts the server on a port chosen by the system (port 0) in a temporary folder: never a fixed
port, never the files of a real project. POST /api/feito records the item as ENVIADO today in every place
the robot records a send (progresso.json, relatorio-parcial.md, company report, draft file,
historico-contatos.md and relatorio-final.xlsx); POST /api/desfazer reverts exactly those writes.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
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
from test_gerar_painel import CHROME, NO_CHROME_REASON, SKIP_RENDER_REASON, dump_panel  # noqa: E402
from test_pendentes import TODAY, make_project  # noqa: E402

GERENTE = "li:linkedin.com/in/gerente-exemplo"
EMAIL3 = "em:3:socio@agencia3.example.com"
FOLLOWUP2 = "fu:2:2026-11-12"
REPORT1 = "relatorios/001-loja-exemplo-1.md"
CONTACTS = "controle/historico-contatos.md"
STATE = "controle/.painel-servidor.json"
FRASE = "Este painel abre pelo comando /painel no Claude Code, ou sozinho no fim de cada rodada do robô."


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
    srv = servidor_painel.make_server(tmp_path, 0, today=TODAY)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    srv.root = tmp_path
    srv.base = f"http://127.0.0.1:{srv.server_address[1]}"
    yield srv
    srv.shutdown()
    srv.server_close()


def call(srv, path, body=None, headers=None, token=True, origin=True):
    """Like the panel page: same Origin, token in the header (GET /data.json and every POST)."""
    h = {"Content-Type": "application/json"}
    if token:
        h["X-Painel-Token"] = srv.token
    if body is not None and origin:
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


def test_serves_the_panel_with_this_runs_token(server):
    code, html = call(server, "/", token=False)
    assert code == 200 and "Pendentes" in html and f'token: "{server.token}"' in html and "__PAINEL_TOKEN__" not in html
    assert call(server, "/data.json")[0] == 200
    assert call(server, "/data.json", token=False)[0] == 403
    code, body = call(server, "/api/estado", token=False)
    assert code == 200 and json.loads(body)["pid"] == os.getpid()
    assert server.server_address[0] == "127.0.0.1"
    other = servidor_painel.make_server(server.root, 0)
    assert other.token != server.token  # a new token on every run, never written to a file
    other.server_close()
    assert not (server.root / "controle" / ".painel-token").exists() and not (server.root / "painel" / "servidor.js").exists()


def test_other_origin_is_refused(server):
    """Only the panel's own address: any other Origin (another site, a file:// page, another port) gets 403."""
    for origin in ("https://example.com", "null", "http://localhost:" + str(server.server_address[1]),
                   "http://127.0.0.1:1"):
        assert call(server, "/api/feito", {"id": GERENTE}, headers={"Origin": origin})[0] == 403, origin
        assert call(server, "/data.json", headers={"Origin": origin})[0] == 403, origin
        code, h, _ = _raw(server, "OPTIONS", "/api/feito", {"Origin": origin, "Access-Control-Request-Method": "POST"})
        assert code != 204 and "access-control-allow-origin" not in h
    assert call(server, "/api/feito", {"id": GERENTE}, origin=False)[0] == 403        # POST without Origin
    assert call(server, "/api/feito", {"id": GERENTE}, token=False)[0] == 403
    assert call(server, "/data.json", headers={"Sec-Fetch-Site": "cross-site"})[0] == 403
    assert call(server, "/", token=False, headers={"Sec-Fetch-Site": "cross-site", "Sec-Fetch-Mode": "no-cors"})[0] == 403
    assert call(server, "/", token=False, headers={"Sec-Fetch-Site": "cross-site", "Sec-Fetch-Mode": "navigate"})[0] == 200
    assert call(server, "/data.json", headers={"Host": "evil.example.com"})[0] == 403
    assert not (server.root / "controle" / "painel-feitos.json").exists()  # nothing was recorded


def _start(root, **env):
    """The real command, in the background, as gerar_painel.py starts it."""
    log = open(root / "srv.log", "wb")
    proc = subprocess.Popen([sys.executable, str(REPO / "scripts" / "servidor_painel.py"), "--raiz", str(root)],
                            cwd=str(root), stdout=log, stderr=log, env=dict(os.environ, **env))
    proc.log = log
    deadline = time.time() + 10
    while time.time() < deadline:
        if gerar_painel.panel_url(root):
            return proc
        time.sleep(0.1)
    proc.kill()
    log.close()
    raise AssertionError((root / "srv.log").read_text(errors="replace"))


def _token(url):
    with urllib.request.urlopen(url, timeout=5) as r:
        return re.search(r'token: "([^"]+)"', r.read().decode("utf-8")).group(1)


def _post(url, body, token):
    origin = url.rstrip("/")
    req = urllib.request.Request(origin + "/api/" + body.pop("_rota"), data=json.dumps(dict(body, token=token)).encode(),
                                 headers={"Content-Type": "application/json", "Origin": origin}, method="POST")
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status


def _ends(proc, root, secs):
    try:
        proc.wait(timeout=secs)
    except subprocess.TimeoutExpired:
        proc.kill()
        return False
    finally:
        proc.log.close()
    return not (root / STATE).exists()


def test_server_starts_fast_and_records_its_state(tmp_path, monkeypatch):
    make_project(tmp_path, monkeypatch)
    t0 = time.time()
    proc = _start(tmp_path)
    try:
        assert time.time() - t0 < 10
        state = json.loads((tmp_path / STATE).read_text(encoding="utf-8"))
        assert set(state) == {"pid", "porta", "iniciado_em"} and state["pid"] == proc.pid
    finally:
        proc.terminate()
        assert _ends(proc, tmp_path, 10)


def test_stops_when_the_tab_is_closed(tmp_path, monkeypatch):
    """pagehide -> sendBeacon('/api/fechou'): the server stops within 20 s and deletes its state file."""
    make_project(tmp_path, monkeypatch)
    proc = _start(tmp_path)
    url = gerar_painel.panel_url(tmp_path)
    token = _token(url)
    assert _post(url, {"_rota": "estado", "pagina": "aba1"}, token) == 200
    t0 = time.time()
    assert _post(url, {"_rota": "fechou", "pagina": "aba1"}, token) == 200
    assert _ends(proc, tmp_path, 20), (tmp_path / "srv.log").read_text(errors="replace")
    assert time.time() - t0 <= 20
    assert gerar_painel.panel_url(tmp_path) is None


def test_stops_without_heartbeat(tmp_path, monkeypatch):
    make_project(tmp_path, monkeypatch)
    proc = _start(tmp_path, PAINEL_SEM_BATIMENTO_S="2")  # 3 minutes in real use
    assert _ends(proc, tmp_path, 15), (tmp_path / "srv.log").read_text(errors="replace")


def test_gerar_painel_reuses_the_running_server(tmp_path, monkeypatch):
    """A second /painel opens the same server: never two servers for the same project."""
    make_project(tmp_path, monkeypatch)
    opened = []
    monkeypatch.setattr(gerar_painel.webbrowser, "open", lambda url: opened.append(url) or True)
    gerar_painel.main([])
    first = json.loads((tmp_path / STATE).read_text(encoding="utf-8"))
    try:
        gerar_painel.main([])
        assert json.loads((tmp_path / STATE).read_text(encoding="utf-8")) == first
        assert opened == [f"http://127.0.0.1:{first['porta']}/"] * 2
    finally:
        try:
            os.kill(first["pid"], 15 if os.name != "nt" else 9)
        except OSError:
            pass
        deadline = time.time() + 10
        while time.time() < deadline and gerar_painel.panel_state(tmp_path):
            time.sleep(0.2)


def _dump(url):
    if not CHROME:
        pytest.skip(NO_CHROME_REASON)
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


def test_file_page_has_no_checkbox():
    """painel/index.html opened straight from disk: only the instruction, no data and no checkbox."""
    html = (REPO / "painel" / "index.html").read_text(encoding="utf-8")
    assert "<input" not in html and "<script" not in html and "data.json" not in html
    assert FRASE in re.sub(r"<[^>]+>", "", html)
    shown = re.sub(r"<[^>]+>", "", _dump((REPO / "painel" / "index.html").as_uri()))
    assert FRASE in shown and "checkbox" not in _dump((REPO / "painel" / "index.html").as_uri())


def test_render_through_server(tmp_path, monkeypatch):
    make_project(tmp_path, monkeypatch)
    html = dump_panel(tmp_path, today=TODAY)
    sec = re.search(r'<section id="pendentes".*?</section>', html, re.S).group(0)
    assert "Enviados hoje" in sec and " disabled" not in sec and sec.count('data-done="') == 13


def test_render_demo_only_strikes(tmp_path):
    """GitHub Pages has no server: the demo fetches its fictitious JSON and the "Feito" only strikes."""
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
    for path in (REPO / "painel" / "index.html", REPO / "scripts" / "painel_template.html", REPO / "docs" / "demo" / "index.html"):
        html = path.read_text(encoding="utf-8")
        foot = re.search(r"<footer>.*?</footer>", html, re.S).group(0)
        assert "Feito por Roni Clei Santos" in foot
        assert 'href="https://www.linkedin.com/in/roni-clei-santos/" target="_blank" rel="noopener">LinkedIn</a>' in foot
        assert 'href="https://github.com/roni-clei-santos/ai-company-prospector" target="_blank" rel="noopener">GitHub</a>' in foot
        assert 'href="https://github.com/roni-clei-santos/ai-company-prospector" target="_blank" rel="noopener">Dar uma estrela no projeto</a>' in foot
