"""Tests for scripts/registrar.py and status normalization (fictitious data only)."""
import json
import sys
from pathlib import Path

import openpyxl
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import common  # noqa: E402
import registrar  # noqa: E402


@pytest.mark.parametrize("raw,expected", [
    ("RASCUNHOS_CRIADOS", ("RASCUNHOS_CRIADOS", None)),
    ("PULADA_PELO_CANDIDATO", ("PULADA_PELO_CANDIDATO", None)),
    ("PULADA_PELO_ALEX (10/11/2026)", ("PULADA_PELO_CANDIDATO", "2026-11-10")),
    ("DESISTENCIA_DO_ALEX", ("DESISTENCIA_DO_CANDIDATO", None)),
    ("VAGA_GESTAO_PARA_O_ALEX_DECIDIR", ("VAGA_GESTAO_PARA_O_CANDIDATO_DECIDIR", None)),
    ("", (None, None)),
])
def test_split_status(raw, expected):
    assert common.split_status(raw) == expected


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setenv("PROSPECT_DIR", str(tmp_path))
    (tmp_path / "controle").mkdir()
    (tmp_path / "perfil.local.md").write_text(
        '```yaml\nplanilha_empresas: "empresas-teste-brasil.xlsx"\ncurriculo_base: "cv.pdf"\n```\n', encoding="utf-8")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Empresas"
    ws.append(["#", "Empresa", "Tipo", "Cidade/UF", "Evidência", "Confiança", "Serve para", "Observação", "Fonte"])
    ws.append([1, "Loja Exemplo 1", "Marca", "Curitiba/PR", "site", "Certeza", "Vaga", "", "https://example.com"])
    ws.append([2, "Loja Exemplo 2", "Marca", "Curitiba/PR", "site", "Provável", "Vaga", "", "https://example.com"])
    wb.save(tmp_path / "empresas-teste-brasil.xlsx")
    return tmp_path


def test_record_creates_both_files(project):
    registrar.record_company({"numero": 2, "empresa": "Loja Exemplo 2",
                              "status": "PULADA_PELO_ALEX (10/11/2026)", "motivo": "teste"})
    prog = json.loads((project / "controle" / "progresso.json").read_text(encoding="utf-8"))
    assert prog["empresas"][0]["status"] == "PULADA_PELO_CANDIDATO"
    assert prog["empresas"][0]["data"] == "2026-11-10"
    ws = openpyxl.load_workbook(project / "relatorio-final.xlsx")["Empresas"]
    header = [c.value for c in ws[1]]
    row = [c.value for c in ws[3]]
    assert row[header.index("Status")] == "PULADA_PELO_CANDIDATO"
    assert row[header.index("Data do status")] == "2026-11-10"
    assert row[header.index("Motivo")] == "teste"


def test_invalid_status_rejected(project):
    with pytest.raises(SystemExit):
        registrar.record_company({"numero": 1, "empresa": "Loja Exemplo 1", "status": "INVENTADO"})


def test_cutoff_and_history(project):
    registrar.main(["--data-corte", "2026-11-09", "--historico", "nota de teste"])
    prog = json.loads((project / "controle" / "progresso.json").read_text(encoding="utf-8"))
    assert prog["data_corte"] == "2026-11-09"
    assert prog["historico"][-1]["nota"] == "nota de teste"


def test_backup_before_each_write(project):
    registrar.main(["--data-corte", "2026-11-09"])
    registrar.main(["--historico", "outra nota"])
    backups = list((project / "controle" / ".backups").glob("progresso-*.json"))
    assert len(backups) == 1  # the first write had nothing to back up
    assert json.loads(backups[0].read_text(encoding="utf-8"))["data_corte"] == "2026-11-09"
