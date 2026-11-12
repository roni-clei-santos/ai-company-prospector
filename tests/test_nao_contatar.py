"""Tests for the NAO_CONTATAR status: people and companies that asked not to be contacted (fictitious data only)."""
import json
import re
import sys
from pathlib import Path

import openpyxl
import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import checar_nao_contatar  # noqa: E402
import common  # noqa: E402
import registrar  # noqa: E402

PERSON = {"nome": "Recrutadora Exemplo", "empresa": "Loja Exemplo 1",
          "email": "recrutadora@example.com", "linkedin_url": "linkedin.com/in/recrutadora-exemplo"}


def test_official_status_list():
    assert "NAO_CONTATAR" in common.OFFICIAL_STATUSES
    assert common.split_status("NAO_CONTATAR (12/11/2026)") == ("NAO_CONTATAR", "2026-11-12")


def test_prompt_status_list_matches_code():
    prompt = (REPO / "PROMPT-prospeccao.md").read_text(encoding="utf-8")
    section = prompt.split("## 12.")[1].split("### 12.1")[0]
    assert re.findall(r"^- `([A-Z_]+)`", section, re.M) == common.OFFICIAL_STATUSES


def test_every_status_has_a_panel_label():
    html = (REPO / "painel" / "index.html").read_text(encoding="utf-8")
    for status in common.OFFICIAL_STATUSES:
        assert f"{status}:" in html, status


def test_next_companies_skill_respects_it():
    skill = (REPO / "skills" / "next-companies" / "SKILL.md").read_text(encoding="utf-8")
    assert "NAO_CONTATAR" in skill and "checar_nao_contatar.py" in skill


@pytest.mark.parametrize("text,expected", [
    ("Para: Recrutadora@Example.com", True),
    ("- Perfil: https://www.linkedin.com/in/recrutadora-exemplo/", True),
    ("- Perfil: https://br.linkedin.com/in/Recrutadora-Exemplo?x=1", True),
    ("- Perfil: https://www.linkedin.com/in/recrutadora-exemplo-2/", False),
    ("## 1) Recrutadora Exemplo — Talent Acquisition", True),
    ("## 1) RECRUTADORA EXEMPLO", True),
    ("## 1) Recrutadora Exemplos", False),
    ("## 1) Outra Pessoa", False),
])
def test_mentions_person(text, expected):
    assert common.mentions_person(text, PERSON) is expected


def test_name_with_accents():
    assert common.mentions_person("Oi, Joao Exemplo", {"nome": "João Exemplo"})
    assert not common.mentions_person("Oi, João", {"nome": "João"})  # one word is too vague to match


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setenv("PROSPECT_DIR", str(tmp_path))
    (tmp_path / "controle").mkdir()
    (tmp_path / "perfil.local.md").write_text(
        '```yaml\nplanilha_empresas: "empresas-teste-brasil.xlsx"\n```\n', encoding="utf-8")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Empresas"
    ws.append(["#", "Empresa", "Tipo"])
    for n in (1, 2, 3):
        ws.append([n, f"Loja Exemplo {n}", "Marca"])
    wb.save(tmp_path / "empresas-teste-brasil.xlsx")
    for sub in ("linkedin", "email"):
        (tmp_path / "rascunhos" / sub).mkdir(parents=True)
    return tmp_path


def progress(project):
    return json.loads((project / "controle" / "progresso.json").read_text(encoding="utf-8"))


def test_company_marked_is_final_and_locked(project):
    registrar.record_company({"numero": 2, "empresa": "Loja Exemplo 2", "status": "NAO_CONTATAR",
                              "motivo": "pediu para não ser contatada"})
    numbers, _ = common.do_not_contact(progress(project))
    assert numbers == {2}
    # /next-companies only picks companies that are NOT in progresso.json > empresas
    assert 2 in {e["numero"] for e in progress(project)["empresas"]}
    with pytest.raises(SystemExit):
        registrar.record_company({"numero": 2, "empresa": "Loja Exemplo 2", "status": "RASCUNHOS_CRIADOS"})
    assert progress(project)["empresas"][0]["status"] == "NAO_CONTATAR"
    registrar.record_company({"numero": 2, "empresa": "Loja Exemplo 2", "status": "RASCUNHOS_CRIADOS"}, force=True)
    assert progress(project)["empresas"][0]["status"] == "RASCUNHOS_CRIADOS"


def test_person_registered_once(project, capsys):
    args = ["--nao-contatar", "Recrutadora Exemplo", "--empresa", "Loja Exemplo 1",
            "--linkedin", "https://www.linkedin.com/in/recrutadora-exemplo/", "--motivo", "pediu por mensagem"]
    registrar.main(args)
    registrar.main(["--nao-contatar", "recrutadora exemplo", "--empresa", "Loja Exemplo 1"])
    people = progress(project)["nao_contatar"]
    assert len(people) == 1
    assert people[0]["linkedin_url"] == "linkedin.com/in/recrutadora-exemplo"
    assert people[0]["motivo"] == "pediu por mensagem" and people[0]["em"]
    assert "already listed" in capsys.readouterr().out
    # same name at another company is another person
    registrar.main(["--nao-contatar", "Recrutadora Exemplo", "--empresa", "Loja Exemplo 3"])
    assert len(progress(project)["nao_contatar"]) == 2


def linkedin_draft(name, url, marker=""):
    return (f"## 1) {marker}{name} — Talent Acquisition\n- Perfil: {url}\n"
            "- Tipo: nota de convite (40 caracteres)\n\n> Oi, tudo certo? Fico à disposição.\n")


def test_checker_ok_without_list(project, capsys):
    (project / "controle" / "progresso.json").write_text('{"empresas": [], "historico": []}', encoding="utf-8")
    (project / "rascunhos" / "linkedin" / "001-loja-exemplo-1.md").write_text(
        linkedin_draft("Recrutadora Exemplo", "https://www.linkedin.com/in/recrutadora-exemplo/"), encoding="utf-8")
    assert checar_nao_contatar.main([str(project)]) == 0
    assert capsys.readouterr().out.strip() == "OK"


def test_checker_flags_pending_draft_to_person(project, capsys):
    registrar.main(["--nao-contatar", "Recrutadora Exemplo", "--email", "recrutadora@example.com"])
    intro = "# Rascunhos LinkedIn — #1 Loja Exemplo 1\n\nContexto: Recrutadora Exemplo cuida das vagas.\n\n"
    (project / "rascunhos" / "linkedin" / "001-loja-exemplo-1.md").write_text(
        intro + linkedin_draft("Recrutadora Exemplo", "https://www.linkedin.com/in/x/")
        + linkedin_draft("Outra Pessoa", "https://www.linkedin.com/in/y/").replace("## 1)", "## 2)"),
        encoding="utf-8")
    (project / "rascunhos" / "email" / "001-loja-exemplo-1-rh.md").write_text(
        "# Rascunho — #1 Loja Exemplo 1\n- Para: recrutadora@example.com\n- Assunto: Oi\n", encoding="utf-8")
    capsys.readouterr()  # drop the registrar output
    assert checar_nao_contatar.main([str(project)]) == 1
    out = capsys.readouterr().out.splitlines()
    assert out[-1] == "PROBLEMAS"
    assert len(out) == 3  # the LinkedIn block of that person + the e-mail (not the intro, not the other person)
    assert any("rascunhos/linkedin/001-loja-exemplo-1.md 5" in line for line in out)
    assert any("rascunhos/email/001-loja-exemplo-1-rh.md 1" in line for line in out)


@pytest.mark.parametrize("marker", ["[ENVIADO 10/11/2026] ", "[NÃO ENVIAR] ", "[NAO ENVIAR] "])
def test_checker_ignores_sent_or_cancelled(project, marker):
    registrar.main(["--nao-contatar", "Recrutadora Exemplo"])
    (project / "rascunhos" / "linkedin" / "001-loja-exemplo-1.md").write_text(
        linkedin_draft("Recrutadora Exemplo", "https://www.linkedin.com/in/x/", marker), encoding="utf-8")
    assert checar_nao_contatar.main([str(project)]) == 0


def test_checker_flags_drafts_of_blocked_company(project, capsys):
    registrar.record_company({"numero": 3, "empresa": "Loja Exemplo 3", "status": "NAO_CONTATAR"})
    (project / "rascunhos" / "linkedin" / "003-loja-exemplo-3.md").write_text(
        "# Rascunhos — #3\n\n" + linkedin_draft("Outra Pessoa", "https://www.linkedin.com/in/y/"), encoding="utf-8")
    (project / "rascunhos" / "linkedin" / "013-loja-exemplo-13.md").write_text(
        linkedin_draft("Outra Pessoa", "https://www.linkedin.com/in/y/"), encoding="utf-8")
    assert checar_nao_contatar.main([str(project)]) == 1
    out = capsys.readouterr().out
    assert "empresa #3: rascunhos/linkedin/003-loja-exemplo-3.md 3" in out
    assert "013-" not in out
