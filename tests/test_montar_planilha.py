"""Tests for scripts/montar_planilha.py (fictitious data only)."""
import json
import sys
from pathlib import Path

import openpyxl
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import montar_planilha  # noqa: E402


def row(name, url, conf="Certeza", **kw):
    base = {"empresa": name, "tipo": "Agência especialista", "cidade_uf": "Curitiba/PR",
            "evidencia": "case público", "confianca": conf, "serve_para": "Vaga", "observacao": "", "fonte": url}
    base.update(kw)
    return base


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setenv("PROSPECT_DIR", str(tmp_path))
    return tmp_path


def test_build_spreadsheet(project):
    data = [
        row("Loja Exemplo 1", "https://loja1.example.com/cases", site="https://loja1.example.com"),
        row("Loja Exemplo 1 Ltda", "https://outra.example.org/x"),            # duplicate by name
        row("Agência Exemplo", "https://news.example.com/a", site="https://www.loja1.example.com"),  # dup by site
        row("Agência Exemplo 2", "https://news.example.com/b"),                 # same source, different company
        row("Sem Fonte", ""),                                                  # no link
        row("Empresa Que Não Quero", "https://nao.example.net"),               # excluded
        row("Antiga Casa", "https://antiga.example.net", conf="Provável"),      # former employer, yellow
    ]
    src = project / "coletadas.json"
    src.write_text(json.dumps(data), encoding="utf-8")
    rc = montar_planilha.main([str(src), "empresas-teste-brasil.xlsx", "--excluir", "Empresa Que Não Quero",
                               "--ex-empregadores", "Antiga Casa", "--titulo", "Teste / Brasil"])
    assert rc == 0
    wb = openpyxl.load_workbook(project / "empresas-teste-brasil.xlsx")
    assert wb.sheetnames == ["Empresas", "Resumo"]
    ws = wb["Empresas"]
    assert [c.value for c in ws[1]] == montar_planilha.HEADER
    names = [r[1] for r in ws.iter_rows(min_row=2, values_only=True)]
    assert names == ["Loja Exemplo 1", "Agência Exemplo 2", "Antiga Casa"]
    assert ws.cell(row=4, column=8).value.startswith("Ex-empregador")
    assert ws.cell(row=4, column=2).fill.fgColor.rgb.endswith("FFF4B3")
    prog = json.loads((project / "controle" / "progresso.json").read_text(encoding="utf-8"))
    assert prog["empresas"] == [] and prog["data_corte"] is None


def test_limit_and_progress_not_overwritten(project):
    (project / "controle").mkdir()
    (project / "controle" / "progresso.json").write_text('{"empresas": [{"numero": 1}], "historico": []}', encoding="utf-8")
    src = project / "c.json"
    src.write_text(json.dumps([row(f"Loja Exemplo {i}", f"https://l{i}.example.com") for i in range(1, 8)]))
    assert montar_planilha.main([str(src), "out.xlsx", "--limite", "3"]) == 0
    ws = openpyxl.load_workbook(project / "out.xlsx")["Empresas"]
    assert ws.max_row == 4
    assert json.loads((project / "controle" / "progresso.json").read_text(encoding="utf-8"))["empresas"] == [{"numero": 1}]


def test_skipped_sources_listed_in_summary(project):
    src = project / "c.json"
    src.write_text(json.dumps([row("Loja Exemplo 1", "https://l1.example.com")]), encoding="utf-8")
    assert montar_planilha.main([str(src), "a.xlsx", "--fontes-fora", "LinkedIn Jobs (Chrome não conectado); Clutch (bloqueou o acesso)"]) == 0
    col = [r[0] for r in openpyxl.load_workbook(project / "a.xlsx")["Resumo"].iter_rows(values_only=True)]
    i = col.index("Fontes que ficaram de fora")
    assert col[i + 1:i + 3] == ["LinkedIn Jobs (Chrome não conectado)", "Clutch (bloqueou o acesso)"]
    assert montar_planilha.main([str(src), "b.xlsx"]) == 0
    col = [r[0] for r in openpyxl.load_workbook(project / "b.xlsx")["Resumo"].iter_rows(values_only=True)]
    assert col[col.index("Fontes que ficaram de fora") + 1].startswith("Nenhuma")
