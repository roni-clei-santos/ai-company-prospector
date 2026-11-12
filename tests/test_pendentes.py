"""Tests for the "Pendentes" tab of the panel (fictitious data only: Loja Exemplo N, example.com).

Covers: the PROMPT 6.0 order of the LinkedIn list, the count check against section 4 of
relatorio-parcial.md, NAO_CONTATAR people and companies never listed, e-mails, follow-ups due,
replies that need an action, decisions, the empty state and the rendered HTML (headless Chrome).
"""
import json
import re
import shutil
import sys
from pathlib import Path

import openpyxl
import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "tests"))
import gerar_painel  # noqa: E402
from test_gerar_painel import CHROME, NO_CHROME_REASON, SKIP_RENDER_REASON  # noqa: E402

TODAY = "2026-11-12"

# companies: (numero, nome, serve_para, confianca)
SHEET = [
    (1, "Loja Exemplo 1", "Prospecção direta (loja)", "Certeza"),
    (2, "Agência Exemplo 2", "Vaga + parceria", "Provável"),
    (3, "Agência Exemplo 3", "Freela/parceria white-label", "Certeza"),
    (4, "Agência Exemplo 4", "Vaga", "Certeza"),
    (5, "Loja Exemplo 5", "Vaga", "Certeza"),
    (6, "Agência Exemplo 6", "Vaga", "Certeza"),
]

PARCIAL = """# Relatório geral (PARCIAL)

## 1. Resumo em números
| Status | Empresas |
|---|---|
| RASCUNHOS_CRIADOS | 6 |

## 2. Ações urgentes que só o candidato pode fazer
1. **Agência Exemplo 4 (#4):** quer se candidatar à vaga Tech Lead Exemplo (gestão)? https://example.com/vagas/tech-lead
2. Enviar as mensagens de LinkedIn da seção 4.

## 3. Rascunhos de e-mail no Gmail (✅ = já enviado)

| # | Para | Assunto | Observação | Cópia |
|---|---|---|---|---|
| 1 ✅ ENVIADO 10/11 | rh@loja1.example.com | Dev Exemplo | apresentação | rascunhos/email/001-loja-exemplo-1.md |
| 3 (criado 11/11) | socio@agencia3.example.com | Parceria Exemplo | Alex Exemplo | parceria | rascunhos/email/003-agencia-exemplo-3.md |
| 6 | rh@agencia6.example.com | Vaga Exemplo | apresentação | rascunhos/email/006-agencia-exemplo-6.md |

## 4. Rascunhos de LinkedIn

| Prio | # | Destinatário | Conexão / tipo | Perfil | Arquivo |
|---|---|---|---|---|---|
| 3 | 1 | Gerente Exemplo — Gerente de E-commerce, Loja Exemplo 1 | não (2º grau) / Tipo: nota de convite | https://www.linkedin.com/in/gerente-exemplo/ | rascunhos/linkedin/001-loja-exemplo-1.md |
| 2 | 2 | Recrutadora Exemplo — Tech Recruiter, Agência Exemplo 2 | não (2º grau) | https://www.linkedin.com/in/recrutadora-exemplo/ | rascunhos/linkedin/002-agencia-exemplo-2.md |
| 2 | 3 | Sócio Exemplo — Sócio, Agência Exemplo 3 (parceria) | sim (1º grau) | https://www.linkedin.com/in/socio-exemplo | rascunhos/linkedin/003-agencia-exemplo-3.md |
| 1 | 4 | Líder Exemplo — Tech Lead, Agência Exemplo 4 | há conversa existente. Responder na própria conversa. | https://www.linkedin.com/in/lider-exemplo/ | rascunhos/linkedin/004-agencia-exemplo-4.md |
| 1 | 4 | Dev Exemplo — Engenheira, Agência Exemplo 4 | sim (1º grau) / Tipo: mensagem direta | https://www.linkedin.com/in/dev-exemplo/ | rascunhos/linkedin/004-agencia-exemplo-4.md |
| ✅ | 5 | **ENVIADO 11/11/2026** Pessoa Enviada — RH, Loja Exemplo 5 | não (2º grau) | https://www.linkedin.com/in/pessoa-enviada/ | rascunhos/linkedin/005-loja-exemplo-5.md |
| — | 5 | **NÃO ENVIAR** (decisão do candidato) Pessoa Bloqueada — RH, Loja Exemplo 5 | não (2º grau) | https://www.linkedin.com/in/pessoa-bloqueada/ | rascunhos/linkedin/005-loja-exemplo-5.md |
| 2 | 6 | Pessoa Que Pediu — RH, Agência Exemplo 6 | não (2º grau) / Tipo: nota de convite | https://www.linkedin.com/in/pessoa-que-pediu/ | rascunhos/linkedin/006-agencia-exemplo-6.md |
| 2 | 6 | Outra Exemplo — Tech Recruiter, Agência Exemplo 6 | não (2º grau) / Tipo: nota de convite | https://www.linkedin.com/in/outra-exemplo/ | rascunhos/linkedin/006-agencia-exemplo-6.md |

## 5. Empresa por empresa (concluídas)
"""

LINKEDIN_FILES = {
    "001-loja-exemplo-1.md": """# Rascunhos LinkedIn — #1 Loja Exemplo 1

## 1) Gerente Exemplo — Gerente de E-commerce
- Perfil: https://www.linkedin.com/in/gerente-exemplo/
- Conexão: não (2º grau) | Tipo: nota de convite

> Oi, Gerente, tudo certinho? Texto de convite da Loja 1.

Mensagem para depois que aceitar:

> Oi, Gerente, obrigado por aceitar. Texto longo da Loja 1.
""",
    "002-agencia-exemplo-2.md": """# Rascunhos LinkedIn — #2 Agência Exemplo 2

## 1) Recrutadora Exemplo — Tech Recruiter
- Perfil: https://www.linkedin.com/in/recrutadora-exemplo/
- Conexão: não (2º grau)
- Tipo: nota de convite

> Oi, Recrutadora, texto da Agência 2.
""",
    "003-agencia-exemplo-3.md": """# Rascunhos LinkedIn — #3 Agência Exemplo 3

## 1) Sócio Exemplo — Sócio
- Perfil: https://www.linkedin.com/in/socio-exemplo
- Conexão: sim (1º grau), sem conversa anterior

> Oi, Sócio, texto de parceria da Agência 3.

> Atualizado em 11/11/2026: nota interna que não é mensagem.
""",
    "004-agencia-exemplo-4.md": """# Rascunhos LinkedIn — #4 Agência Exemplo 4

## 1) Dev Exemplo — Engenheira
- Perfil: https://www.linkedin.com/in/dev-exemplo/
- Conexão: sim (1º grau)
- Tipo: mensagem direta

> Oi, Dev, texto da Agência 4.

---
## RETOMADA (regra P1)

### 2) Líder Exemplo — Tech Lead
- Perfil: https://www.linkedin.com/in/lider-exemplo/
- Conexão: há conversa existente (2024). Responder na própria conversa.
- Tipo: mensagem na conversa existente

> Oi, Líder, quanto tempo! Texto de retomada.
""",
    "006-agencia-exemplo-6.md": """# Rascunhos LinkedIn — #6 Agência Exemplo 6

## 1) Pessoa Que Pediu — RH
- Perfil: https://www.linkedin.com/in/pessoa-que-pediu/
- Tipo: nota de convite

> Oi, texto que não pode aparecer.

## 2) Outra Exemplo — Tech Recruiter
- Perfil: https://www.linkedin.com/in/outra-exemplo/
- Tipo: nota de convite

> Oi, Outra, texto da Agência 6.
""",
}

EMAIL_FILES = {
    "003-agencia-exemplo-3.md": "# Rascunho\n- Para: socio@agencia3.example.com\n- Assunto: Parceria Exemplo | Alex Exemplo\n\nOi, Sócio.\n\nCorpo do e-mail.\n",
    "006-agencia-exemplo-6.md": "# Rascunho\n- Para: rh@agencia6.example.com\n- Assunto: Vaga Exemplo\n\nCorpo.\n",
}

ROUND = """# Rodada de 11/11/2026: 6 empresas (#1 a #6)

## Envios que encontrei (registrados)
- Responderam em 10/11: Recrutadora Exemplo (#2) pediu o currículo; Gerente Exemplo (#1) pediu o link (você mandou); Pessoa Que Pediu (#6) pediu para não ser contatada

## Resumo
- **Rascunhos novos:** 2 e-mails e 7 mensagens de LinkedIn.

## Empresa por empresa

| # | Empresa | Status | Motivo (1 linha) | Candidaturas |
|---|---|---|---|---|
| 1 | Loja Exemplo 1 | RASCUNHOS_CRIADOS | teste | Nenhuma |

## O que depende do candidato
1. Enviar as mensagens de LinkedIn.
2. Opcional: a vaga Dev Exemplo da Loja Exemplo 5 (https://example.com/vagas/dev-ingles) pede inglês fluente. Não me candidatei; a decisão é sua.
3. Follow-ups opcionais, só se não houver resposta:
   - Gerente Exemplo (Loja Exemplo 1, #1): a partir de 10/11/2026;
   - Recrutadora Exemplo (Agência Exemplo 2, #2): a partir de 12/11/2026;
   - Pessoa Que Pediu (Agência Exemplo 6, #6): a partir de 01/11/2026;
   - Sócio Exemplo (Agência Exemplo 3, #3): a partir de 30/11/2099.
"""


def make_project(tmp_path, monkeypatch, parcial=PARCIAL, nao_contatar=True, rounds=(("rodada-2026-11-11.md", ROUND),)):
    monkeypatch.setenv("PROSPECT_DIR", str(tmp_path))
    for sub in ("controle", "relatorios", "painel", "rascunhos/linkedin", "rascunhos/email"):
        (tmp_path / sub).mkdir(parents=True)
    shutil.copy(REPO / "painel" / "index.html", tmp_path / "painel" / "index.html")
    (tmp_path / "perfil.local.md").write_text('```yaml\nmodo_email: "gmail_rascunho"\n```\n', encoding="utf-8")
    prog = {"data_corte": "2026-11-09", "historico": [],
            "empresas": [{"numero": n, "empresa": name, "status": "RASCUNHOS_CRIADOS", "data": "2026-11-11"}
                         for n, name, _, _ in SHEET]}
    if nao_contatar:
        prog["nao_contatar"] = [{"nome": "Pessoa Que Pediu", "empresa": "Agência Exemplo 6",
                                 "linkedin_url": "linkedin.com/in/pessoa-que-pediu", "pedido_em": "2026-11-10"}]
    (tmp_path / "controle" / "progresso.json").write_text(json.dumps(prog, ensure_ascii=False), encoding="utf-8")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Empresas"
    ws.append(["#", "Empresa", "Tipo", "Confiança", "Serve para", "Status"])
    for n, name, serve, conf in SHEET:
        ws.append([n, name, "Agência", conf, serve, "RASCUNHOS_CRIADOS"])
    wb.save(tmp_path / "relatorio-final.xlsx")
    if parcial is not None:
        (tmp_path / "relatorio-parcial.md").write_text(parcial, encoding="utf-8")
    for name, text in LINKEDIN_FILES.items():
        (tmp_path / "rascunhos" / "linkedin" / name).write_text(text, encoding="utf-8")
    for name, text in EMAIL_FILES.items():
        (tmp_path / "rascunhos" / "email" / name).write_text(text, encoding="utf-8")
    for name, text in rounds:
        (tmp_path / "relatorios" / name).write_text(text, encoding="utf-8")
    data = gerar_painel.build(tmp_path, today=TODAY)
    out = tmp_path / "painel"
    payload = json.dumps(data, ensure_ascii=False)
    (out / "data.json").write_text(payload, encoding="utf-8")
    (out / "data.js").write_text(f"window.PAINEL_DATA = {payload};\n", encoding="utf-8")
    return data


def test_count_section4_matches_panel(tmp_path, monkeypatch):
    data = make_project(tmp_path, monkeypatch)
    p = data["pendentes"]
    # 9 rows: 1 ✅ and 1 NÃO ENVIAR are out -> 7 pending in section 4; 1 hidden by NAO_CONTATAR -> 6 listed
    assert gerar_painel.count_linkedin_section4(PARCIAL) == 7
    assert p["conferencia"] == {"linkedin_secao4": 7, "linkedin_painel": 6, "ocultos_nao_contatar": 1,
                                "fonte": "relatorio-parcial.md"}
    assert p["conferencia"]["linkedin_secao4"] == p["conferencia"]["linkedin_painel"] + p["conferencia"]["ocultos_nao_contatar"]
    assert p["totais"]["linkedin"] == len(p["linkedin"]) == 6


def test_count_equal_without_nao_contatar(tmp_path, monkeypatch):
    data = make_project(tmp_path, monkeypatch, nao_contatar=False)
    c = data["pendentes"]["conferencia"]
    assert c["linkedin_secao4"] == c["linkedin_painel"] == 7 and c["ocultos_nao_contatar"] == 0


def test_linkedin_order_follows_prompt_section_6(tmp_path, monkeypatch):
    li = make_project(tmp_path, monkeypatch)["pendentes"]["linkedin"]
    # 6.0: Vaga/Certeza (#4, #6) -> Vaga/Provável (#2) -> Freela (#3) -> Prospecção direta (#1);
    # inside a company, the order of section 4 is kept (Líder before Dev)
    assert [(it["ordem"], it["numero"], it["nome"]) for it in li] == [
        (1, 4, "Líder Exemplo"), (2, 4, "Dev Exemplo"), (3, 6, "Outra Exemplo"),
        (4, 2, "Recrutadora Exemplo"), (5, 3, "Sócio Exemplo"), (6, 1, "Gerente Exemplo")]


def test_linkedin_item_fields(tmp_path, monkeypatch):
    li = {it["nome"]: it for it in make_project(tmp_path, monkeypatch)["pendentes"]["linkedin"]}
    g = li["Gerente Exemplo"]
    assert g["empresa"] == "Loja Exemplo 1" and g["cargo"] == "Gerente de E-commerce, Loja Exemplo 1"
    assert g["perfil"] == "https://www.linkedin.com/in/gerente-exemplo/"
    assert (g["tipo"], g["tipo_rotulo"]) == ("convite", "Convite com nota")
    assert g["texto"] == "Oi, Gerente, tudo certinho? Texto de convite da Loja 1."
    assert g["extras"] == [{"rotulo": "Mensagem para depois que aceitar", "texto": "Oi, Gerente, obrigado por aceitar. Texto longo da Loja 1."}]
    assert li["Líder Exemplo"]["tipo_rotulo"] == "Mensagem direta (na conversa que já existe)"
    assert li["Líder Exemplo"]["texto"] == "Oi, Líder, quanto tempo! Texto de retomada."
    assert (li["Dev Exemplo"]["tipo"], li["Sócio Exemplo"]["tipo"]) == ("mensagem", "mensagem")  # 1º grau, no Tipo line
    assert li["Sócio Exemplo"]["extras"] == []  # the "Atualizado em" note is not a message
    assert li["Recrutadora Exemplo"]["tipo"] == "convite"


def test_nao_contatar_never_listed(tmp_path, monkeypatch):
    data = make_project(tmp_path, monkeypatch)
    blob = json.dumps(data["pendentes"], ensure_ascii=False) + json.dumps(data["followups"], ensure_ascii=False)
    assert "Pessoa Que Pediu" not in blob and "texto que não pode aparecer" not in blob
    assert "Pessoa Bloqueada" not in blob and "Pessoa Enviada" not in blob


def test_nao_contatar_company_hides_everything_from_it(tmp_path, monkeypatch):
    make_project(tmp_path, monkeypatch, nao_contatar=False)
    prog_path = tmp_path / "controle" / "progresso.json"
    prog = json.loads(prog_path.read_text(encoding="utf-8"))
    prog["empresas"][5]["status"] = "NAO_CONTATAR"  # #6 Agência Exemplo 6
    prog_path.write_text(json.dumps(prog), encoding="utf-8")
    data = gerar_painel.build(tmp_path, today=TODAY)
    p = data["pendentes"]
    assert all(it["numero"] != 6 for it in p["linkedin"] + p["emails"] + p["decisoes"])
    assert all(6 not in f["numeros"] for f in data["followups"])
    assert p["conferencia"]["ocultos_nao_contatar"] == 2


def test_emails_pending_only(tmp_path, monkeypatch):
    em = make_project(tmp_path, monkeypatch)["pendentes"]["emails"]
    assert [(e["numero"], e["para"]) for e in em] == [(3, "socio@agencia3.example.com"), (6, "rh@agencia6.example.com")]
    assert em[0]["assunto"] == "Parceria Exemplo | Alex Exemplo"  # an unescaped '|' in the table is rebuilt from the draft
    assert "texto" not in em[0]  # Gmail mode: the panel links to Gmail > Rascunhos


def test_followups_due_and_replies(tmp_path, monkeypatch):
    data = make_project(tmp_path, monkeypatch)
    p = data["pendentes"]
    due = [f["quem"] for f in data["followups"] if f["data"] <= TODAY]
    assert due == ["Gerente Exemplo (Loja Exemplo 1, #1)", "Recrutadora Exemplo (Agência Exemplo 2, #2)"]
    assert p["totais"]["followups_vencidos"] == 2
    # only the reply that asks something and was not handled yet; NAO_CONTATAR is never listed
    assert [r["texto"] for r in p["respostas"]] == ["Recrutadora Exemplo (#2) pediu o currículo"]


def test_decisions_from_rounds_and_report(tmp_path, monkeypatch):
    dec = {d["numero"]: d for d in make_project(tmp_path, monkeypatch)["pendentes"]["decisoes"]}
    assert set(dec) == {4, 5}
    assert dec[4]["link"] == "https://example.com/vagas/tech-lead" and dec[4]["origem"] == "relatorio-parcial.md"
    assert dec[5]["link"] == "https://example.com/vagas/dev-ingles" and dec[5]["origem"] == "rodada de 11/11"
    assert "inglês fluente" in dec[5]["motivo"]


def test_followups_merge_every_round(tmp_path, monkeypatch):
    older = ROUND.replace("a partir de 10/11/2026", "a partir de 05/11/2026") + "   - Loja Exemplo 5 (#5): a partir de 09/11/2026.\n"
    data = make_project(tmp_path, monkeypatch, rounds=(("rodada-2026-11-10.md", older), ("rodada-2026-11-11.md", ROUND)))
    by_num = {tuple(f["numeros"]): f["data"] for f in data["followups"]}
    assert by_num[(1,)] == "2026-11-10"  # the newer round wins
    assert by_num[(5,)] == "2026-11-09"  # only in the older round: still listed


def test_empty_project(tmp_path, monkeypatch):
    data = make_project(tmp_path, monkeypatch, parcial=None, rounds=())
    p = data["pendentes"]
    assert p["linkedin"] == p["emails"] == p["decisoes"] == p["respostas"] == []
    assert p["conferencia"]["linkedin_secao4"] == 0 and p["conferencia"]["fonte"] is None


def _render(tmp_path):
    if not CHROME:
        pytest.skip(NO_CHROME_REASON)
    import os
    import subprocess
    import tempfile
    profile = tempfile.mkdtemp(prefix="chrome-test-")
    try:
        return subprocess.run([CHROME, "--headless=new", "--disable-gpu", f"--user-data-dir={profile}", "--no-first-run",
                               "--no-default-browser-check", "--virtual-time-budget=3000", "--dump-dom",
                               (tmp_path / "painel" / "index.html").as_uri()],
                              capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30).stdout
    except subprocess.TimeoutExpired:
        if os.environ.get("CI") == "true" and sys.platform == "darwin":
            pytest.skip(SKIP_RENDER_REASON)
        raise
    finally:
        shutil.rmtree(profile, ignore_errors=True)


def test_rendered_tab(tmp_path, monkeypatch):
    make_project(tmp_path, monkeypatch)
    html = _render(tmp_path)
    nav = re.search(r'<nav class="tabs".*?</nav>', html, re.S).group(0)
    assert re.findall(r'href="#(\w+)"', nav)[0] == "pendentes"  # first tab
    assert re.search(r'<a href="#pendentes" class="on"', nav)  # open by default
    assert re.search(r'<section id="pendentes"[^>]*>', html) and not re.search(r'<section id="pendentes"[^>]*hidden', html)
    assert re.search(r'<section id="rodada"[^>]*hidden', html)
    sec = re.search(r'<section id="pendentes".*?</section>', html, re.S).group(0)
    text = re.sub(r"<[^>]+>", "", sec)
    # the browser date decides what is due; the fixture dates are in the past, so both are due
    assert "6 mensagens de LinkedIn, 2 e-mails, 2 follow-ups vencidos e 2 decisões suas" in text
    assert sec.count('class="task') == 2 + 1 + 6 + 2 + 2  # hoje (2 follow-ups + 1 resposta) + LinkedIn + e-mails + decisões
    assert sec.count("Abrir perfil") == 6 and sec.count("Abrir Rascunhos do Gmail") == 2
    assert sec.count('href="https://mail.google.com/mail/u/0/#drafts"') == 2
    assert sec.count('data-done="') == 13 and "Copiar texto" in sec
    assert "Pessoa Que Pediu" not in sec
    assert "Nada pendente aqui" not in sec


def test_rendered_empty_sections(tmp_path, monkeypatch):
    make_project(tmp_path, monkeypatch, parcial=None, rounds=())
    sec = re.search(r'<section id="pendentes".*?</section>', _render(tmp_path), re.S).group(0)
    assert sec.count("Nada pendente aqui") == 4
    assert "0 mensagens de LinkedIn, 0 e-mails, 0 follow-ups vencidos e 0 decisões suas" in re.sub(r"<[^>]+>", "", sec)


def test_painel_skill_only_opens_the_panel():
    """/painel runs scripts/gerar_painel.py and nothing else: no LinkedIn, Gmail or Chrome."""
    skill = (REPO / "skills" / "painel" / "SKILL.md").read_text(encoding="utf-8")
    assert skill.startswith("---\nname: painel\n")
    assert "scripts/gerar_painel.py" in skill
    assert re.search(r"PROIBIDO nesta skill: abrir ou usar o LinkedIn, o Gmail, o Chrome", skill)
    assert "preflight-linkedin" not in skill and "tabs_context_mcp" not in skill
    assert "Não achei o projeto. Rode o instalador na pasta do projeto." in skill
