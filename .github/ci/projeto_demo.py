#!/usr/bin/env python3
"""CI helper: create a small project with FICTITIOUS demo data (Loja Exemplo N) in <folder>.

Used by .github/workflows/test.yml to run `scripts/gerar_painel.py --no-open` on every system.
Usage: python .github/ci/projeto_demo.py <folder>            create the project
       python .github/ci/projeto_demo.py <folder> --check    after gerar_painel.py: check the "Pendentes" tab
"""
import json
import shutil
import sys
from pathlib import Path

import openpyxl

REPO = Path(__file__).resolve().parents[2]


def main(folder):
    root = Path(folder)
    for sub in ("controle", "relatorios", "painel", "rascunhos/linkedin"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO / "painel" / "index.html", root / "painel" / "index.html")
    statuses = ["RASCUNHOS_CRIADOS", "CANDIDATURA_ENVIADA", "NAO_ELEGIVEL", "RASCUNHOS_CRIADOS", "SEM_OPORTUNIDADE"]
    empresas = [{"numero": n, "empresa": f"Loja Exemplo {n}", "status": st, "data": "2026-11-11",
                 "atualizado_em": "2026-11-11 10:00"} for n, st in enumerate(statuses, 1)]
    (root / "controle" / "progresso.json").write_text(json.dumps(
        {"data_corte": "2026-11-09", "empresas": empresas,
         "historico": [{"em": "2026-11-11", "nota": "Rodada de demonstração (dados fictícios)."}]},
        ensure_ascii=False, indent=2), encoding="utf-8")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Empresas"
    ws.append(["#", "Empresa", "Tipo", "Status"])
    for n in range(1, 9):
        ws.append([n, f"Loja Exemplo {n}", "Marca/varejista que usa a tecnologia", statuses[n - 1] if n <= 5 else None])
    wb.save(root / "relatorio-final.xlsx")
    (root / "relatorios" / "rodada-2026-11-11.md").write_text(
        "# Rodada de 11/11/2026: 5 empresas (#1 a #5)\n\n## Envios que encontrei (registrados)\n"
        "- Responderam em 10/11: Recrutadora Exemplo (#1) pediu o currículo\n\n## Resumo\n"
        "- **Status:** 2 RASCUNHOS_CRIADOS, 1 CANDIDATURA_ENVIADA, 1 NAO_ELEGIVEL, 1 SEM_OPORTUNIDADE.\n\n"
        "## O que depende do candidato\n1. Enviar 3 mensagens de LinkedIn.\n", encoding="utf-8")
    (root / "relatorio-parcial.md").write_text(
        "# Relatório (PARCIAL)\n\n## 3. Rascunhos de e-mail\n\n| # | Para | Assunto | Observação | Cópia |\n|---|---|---|---|---|\n"
        "| 1 | rh@loja1.example.com | Dev Exemplo | apresentação | rascunhos/email/001-loja-exemplo-1.md |\n\n"
        "## 4. Rascunhos de LinkedIn\n\n| Prio | # | Destinatário | Conexão / tipo | Perfil | Arquivo |\n|---|---|---|---|---|---|\n"
        "| 2 | 1 | Recrutadora Exemplo — Tech Recruiter, Loja Exemplo 1 | não (2º grau) / Tipo: nota de convite | "
        "https://www.linkedin.com/in/recrutadora-exemplo/ | rascunhos/linkedin/001-loja-exemplo-1.md |\n"
        "| ✅ | 4 | **ENVIADO 11/11/2026** Gerente Exemplo — Gerente, Loja Exemplo 4 | não (2º grau) | "
        "https://www.linkedin.com/in/gerente-exemplo/ | rascunhos/linkedin/004-loja-exemplo-4.md |\n\n## 5. Empresa por empresa\n",
        encoding="utf-8")
    (root / "rascunhos" / "linkedin" / "001-loja-exemplo-1.md").write_text(
        "# Rascunhos LinkedIn — #1 Loja Exemplo 1\n\n## 1) Recrutadora Exemplo — Tech Recruiter\n"
        "- Perfil: https://www.linkedin.com/in/recrutadora-exemplo/\n- Tipo: nota de convite\n\n> Oi, Recrutadora, tudo certinho?\n",
        encoding="utf-8")
    print(f"Projeto de demonstração criado em {root}")


def check(folder):
    """The panel built from this project must list 1 LinkedIn message and 1 e-mail, and the count must match section 4."""
    p = json.loads((Path(folder) / "painel" / "data.json").read_text(encoding="utf-8"))["pendentes"]
    c = p["conferencia"]
    assert c["linkedin_secao4"] == c["linkedin_painel"] + c["ocultos_nao_contatar"] == 1, c
    assert p["linkedin"][0]["texto"] == "Oi, Recrutadora, tudo certinho?", p["linkedin"]
    assert len(p["emails"]) == 1, p["emails"]
    print(f"Pendentes OK: {c['linkedin_painel']} LinkedIn (seção 4: {c['linkedin_secao4']}), {len(p['emails'])} e-mail")


if __name__ == "__main__":
    if "--check" in sys.argv[2:]:
        check(sys.argv[1])
    else:
        main(sys.argv[1])
