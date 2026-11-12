"""Tests for the web mode (docs/web/PROMPT-planilha*.md) and its spreadsheet (fictitious data only)."""
import json
import re
import sys
from pathlib import Path

import openpyxl
import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import gerar_painel  # noqa: E402
import montar_planilha  # noqa: E402
import registrar  # noqa: E402

WEB_COLUMNS = montar_planilha.HEADER + ["Primeira mensagem (rascunho)"]
PROMPTS = {
    "pt": (REPO / "docs/web/PROMPT-planilha.md",
           "Para mais empresas, abra uma conversa nova, cole este mesmo texto e anexe a planilha que você baixou. "
           "Eu continuo sem repetir nenhuma."),
    "en": (REPO / "docs/web/PROMPT-planilha.en.md",
           "For more companies, open a new chat, paste this same text and attach the spreadsheet you downloaded. "
           "I'll continue without repeating any."),
}


def prompt_text(path):
    """The text the person copies: the single ```text block of the file."""
    blocks = re.findall(r"```text\n(.*?)\n```", path.read_text(encoding="utf-8"), re.S)
    assert len(blocks) == 1
    return blocks[0]


@pytest.mark.parametrize("lang", PROMPTS)
def test_prompt_has_every_step(lang):
    path, closing = PROMPTS[lang]
    text = prompt_text(path)
    assert ", ".join(WEB_COLUMNS) in text  # same columns as the robot + the draft message
    assert text.rstrip().endswith(closing + '"')
    assert "25" in text and "300" in text and "Indeed" in text
    for stage in range(6):  # 0 attached sheet, 1 questions, 2 research, 3 message, 4 Excel/text, 5 answer
        assert re.search(rf"^(ETAPA|STEP) {stage}\.", text, re.M), stage
    questions = re.split(r"^(?:ETAPA|STEP) [12]\.", text, flags=re.M)[1]  # the Step 1 block
    assert re.findall(r"^([1-9])\. ", questions, re.M) == ["1", "2", "3", "4", "5", "6"]


@pytest.mark.parametrize("lang", PROMPTS)
def test_images_exist(lang):
    path = PROMPTS[lang][0]
    images = re.findall(r'<img src="([^"]+)"', path.read_text(encoding="utf-8"))
    assert len(images) == 3
    for img in images:
        assert (path.parent / img).is_file(), img


def test_readmes_point_to_the_three_paths():
    for name, prompt in (("README.md", "docs/web/PROMPT-planilha.md"), ("README.en.md", "docs/web/PROMPT-planilha.en.md")):
        text = (REPO / name).read_text(encoding="utf-8")
        assert prompt in text, name
        for url in ("support.claude.com/en/articles/10684626", "support.claude.com/en/articles/12111783",
                    "support.claude.com/en/articles/12012173", "claude.com/pricing"):
            assert url in text, (name, url)
    assert (REPO / "docs/guia/00-sem-instalar.md").is_file()


@pytest.fixture
def web_project(tmp_path, monkeypatch):
    """A project folder whose company sheet was downloaded from the web mode."""
    monkeypatch.setenv("PROSPECT_DIR", str(tmp_path))
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Empresas"
    ws.append(WEB_COLUMNS)
    ws.append([1, "Loja Exemplo 1", "Agência especialista", "Curitiba/PR", "parceira oficial", "Certeza", "Vaga",
               "", "https://example.com/1", "Oi! Vi que vocês são parceiros oficiais. [1 frase sobre você]"])
    ws.append([2, "Loja Exemplo 2", "Marca/varejista que usa a tecnologia", "Remoto", "loja roda a tecnologia",
               "Provável", "Prospecção direta (loja)", "", "https://example.com/2", "Oi! [seu nome] aqui."])
    wb.create_sheet("Resumo").append(["Pesquisa", "Magento / Brasil / todos / todos / nenhuma / nenhum / lote 2"])
    wb.save(tmp_path / "empresas-magento-brasil.xlsx")
    (tmp_path / "perfil.local.md").write_text('```yaml\nplanilha_empresas: "empresas-magento-brasil.xlsx"\n```\n',
                                             encoding="utf-8")
    return tmp_path


def test_web_sheet_works_with_the_robot(web_project):
    registrar.main(["--data-corte", "2026-11-12"])  # guide 00, "E depois?": creates controle/progresso.json
    assert json.loads((web_project / "controle" / "progresso.json").read_text(encoding="utf-8"))["empresas"] == []
    registrar.record_company({"numero": 2, "empresa": "Loja Exemplo 2", "status": "SEM_OPORTUNIDADE"})
    ws = openpyxl.load_workbook(web_project / "relatorio-final.xlsx")["Empresas"]
    header = [c.value for c in ws[1]]
    assert header[:len(WEB_COLUMNS)] == WEB_COLUMNS
    row = [c.value for c in ws[3]]
    assert row[header.index("Status")] == "SEM_OPORTUNIDADE"
    assert row[header.index("Primeira mensagem (rascunho)")] == "Oi! [seu nome] aqui."
    prog = json.loads((web_project / "controle" / "progresso.json").read_text(encoding="utf-8"))
    types, total = gerar_painel.company_types(web_project, {e["numero"]: e["status"] for e in prog["empresas"]})
    assert total == 2 and {t["tipo"] for t in types} == {"Agência especialista", "Marca/varejista que usa a tecnologia"}
