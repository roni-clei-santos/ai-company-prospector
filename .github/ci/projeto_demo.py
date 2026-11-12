#!/usr/bin/env python3
"""CI helper: create a small project with FICTITIOUS demo data (Loja Exemplo N) in <folder>.

Used by .github/workflows/test.yml to run `scripts/gerar_painel.py --no-open` on every system.
Usage: python .github/ci/projeto_demo.py <folder>
"""
import json
import shutil
import sys
from pathlib import Path

import openpyxl

REPO = Path(__file__).resolve().parents[2]


def main(folder):
    root = Path(folder)
    for sub in ("controle", "relatorios", "painel"):
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
    print(f"Projeto de demonstração criado em {root}")


if __name__ == "__main__":
    main(sys.argv[1])
