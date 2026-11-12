"""Tests for scripts/gerar_painel.py: the follow-up item of "O que fazer agora" (fictitious data only).

Each case checks painel/data.json and the HTML rendered by painel/index.html (via headless Chrome,
skipped when Chrome is not installed).
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import openpyxl
import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import gerar_painel  # noqa: E402

CHROME = next((p for p in [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    shutil.which("google-chrome") or "", shutil.which("chromium") or "",
] if p and Path(p).exists()), None)

ROUND_HEAD = """# Rodada de 11/11/2026: 3 empresas (#1 a #3)

## Envios que encontrei (registrados)
- Responderam em 10/11: Recrutadora Exemplo (#1) pediu o currículo

## Resumo
- **Status:** 3 RASCUNHOS_CRIADOS.
- **Candidaturas enviadas:** 0.
- **Rascunhos novos:** 1 e-mail e 2 mensagens de LinkedIn.

## Empresa por empresa

| # | Empresa | Status | Motivo (1 linha) | Candidaturas |
|---|---|---|---|---|
| 1 | Loja Exemplo 1 | RASCUNHOS_CRIADOS | teste | Nenhuma |
| 2 | Loja Exemplo 2 | RASCUNHOS_CRIADOS | teste | Nenhuma |
| 3 | Loja Exemplo 3 | RASCUNHOS_CRIADOS | teste | Nenhuma |

## O que depende do candidato
1. Enviar as 2 mensagens de LinkedIn.
"""
WITH_FOLLOWUPS = ROUND_HEAD + """2. Follow-ups opcionais, só se não houver resposta:
   - Recrutadora Exemplo (Loja Exemplo 1, #1): a partir de 12/11/2026;
   - Loja Exemplo 2 (#2) e Gerente Exemplo (Loja Exemplo 3, #3): a partir de 20/11/2026.
3. Conferir o e-mail da Loja Exemplo 2.
"""
WITHOUT_FOLLOWUPS = ROUND_HEAD + """2. Follow-ups opcionais, só se não houver resposta:
3. Conferir o e-mail da Loja Exemplo 2.
"""


def make_project(tmp_path, monkeypatch, round_text):
    monkeypatch.setenv("PROSPECT_DIR", str(tmp_path))
    (tmp_path / "controle").mkdir()
    (tmp_path / "relatorios").mkdir()
    (tmp_path / "painel").mkdir()
    shutil.copy(REPO / "painel" / "index.html", tmp_path / "painel" / "index.html")
    (tmp_path / "controle" / "progresso.json").write_text(json.dumps({
        "data_corte": "2026-11-09", "historico": [],
        "empresas": [{"numero": n, "empresa": f"Loja Exemplo {n}", "status": "RASCUNHOS_CRIADOS",
                      "data": "2026-11-11", "atualizado_em": "2026-11-11 10:00"} for n in (1, 2, 3)]}))
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Empresas"
    ws.append(["#", "Empresa", "Tipo", "Status"])
    for n in range(1, 6):
        ws.append([n, f"Loja Exemplo {n}", "Marca/varejista que usa a tecnologia", "RASCUNHOS_CRIADOS" if n <= 3 else None])
    wb.save(tmp_path / "relatorio-final.xlsx")
    (tmp_path / "relatorios" / "rodada-2026-11-11.md").write_text(round_text, encoding="utf-8")
    gerar_painel.main()
    return json.loads((tmp_path / "painel" / "data.json").read_text(encoding="utf-8"))


def render(tmp_path):
    out = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--virtual-time-budget=3000", "--dump-dom",
                          (tmp_path / "painel" / "index.html").as_uri()],
                         capture_output=True, text=True, timeout=60).stdout
    m = re.search(r'<ol class="todo">(.*?)</ol>', out, re.S)
    assert m, "to-do list not rendered"
    return m.group(1)


def test_with_followups(tmp_path, monkeypatch):
    data = make_project(tmp_path, monkeypatch, WITH_FOLLOWUPS)
    todo = data["rodada"]["o_que_fazer"]
    assert [t["texto"] for t in todo] == [
        "Enviar as 2 mensagens de LinkedIn.",
        "Follow-ups opcionais, só se não houver resposta:",
        "Conferir o e-mail da Loja Exemplo 2.",
    ]
    assert todo[1]["subitens"] == ["12/11 — Loja Exemplo 1 (#1)", "20/11 — Loja Exemplo 2 (#2) e Loja Exemplo 3 (#3)"]
    assert len(data["followups"]) == 2
    if CHROME:
        html = render(tmp_path)
        assert html.count('<ul class="sub">') == 1
        assert "12/11 — Loja Exemplo 1 (#1)" in html
        assert "20/11 — Loja Exemplo 2 (#2) e Loja Exemplo 3 (#3)" in html


def test_without_followups(tmp_path, monkeypatch):
    data = make_project(tmp_path, monkeypatch, WITHOUT_FOLLOWUPS)
    todo = data["rodada"]["o_que_fazer"]
    assert [t["texto"] for t in todo] == ["Enviar as 2 mensagens de LinkedIn.", "Conferir o e-mail da Loja Exemplo 2."]
    assert data["followups"] == []
    if CHROME:
        html = render(tmp_path)
        assert "Follow-ups" not in html
        assert '<ul class="sub">' not in html
        # an <ol> numbers its <li> items itself: two top-level items -> 1. and 2.
        assert len(re.findall(r"<li>", html)) == 2


def test_followup_label_formats():
    lab = gerar_painel.followup_label
    assert lab({"quem": "Tech Lead Exemplo (Agência Exemplo 7, #27)", "data": "2026-11-18"}) == "18/11 — Agência Exemplo 7 (#27)"
    assert lab({"quem": "Loja Exemplo 9 (#9)", "data": "2026-11-20"}) == "20/11 — Loja Exemplo 9 (#9)"
    assert lab({"quem": "Alguém sem número", "data": "2026-12-01"}) == "01/12 — Alguém sem número"
