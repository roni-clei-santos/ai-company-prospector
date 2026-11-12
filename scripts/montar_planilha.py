#!/usr/bin/env python3
"""Build the company spreadsheet (empresas-<tecnologia>-<pais>.xlsx) from a JSON list.

Usage (from the project folder):
  python3 scripts/montar_planilha.py <companies.json> <output.xlsx> [--excluir "A;B"] [--ex-empregadores "C;D"]
                                     [--limite N] [--titulo "Magento / Adobe Commerce"]

companies.json: a list of objects with keys
  empresa, tipo, cidade_uf, evidencia, confianca ("Certeza" | "Provável"), serve_para, observacao, fonte,
  and optionally site (the company's own website, used only to detect duplicates)
Rules enforced here:
  - every row needs a source link (fonte starting with http) and evidence; rows without are rejected;
  - duplicates (same normalized name or same `site` domain) are dropped, keeping the first;
  - excluded companies are dropped; former employers get "Ex-empregador" in Observação;
  - "Provável" rows are highlighted in yellow.
It also creates controle/progresso.json (empty, ready for /next-companies) if it does not exist.
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import project_root, read_profile_fields, write_json_atomic  # noqa: E402

HEADER = ["#", "Empresa", "Tipo", "Cidade/UF", "Evidência", "Confiança", "Serve para", "Observação", "Fonte"]
KEYS = ["empresa", "tipo", "cidade_uf", "evidencia", "confianca", "serve_para", "observacao", "fonte"]
TYPES = [
    "Agência especialista",
    "Consultoria/integradora grande",
    "Agência digital multiplataforma",
    "Marca/varejista que usa a tecnologia",
    "Empresa com vaga aberta",
    "Internacional que contrata remoto na região",
    "Ecossistema (módulo/plataforma sobre a tecnologia)",
]
SERVE = ["Vaga", "Vaga + parceria", "Freela/parceria white-label", "Prospecção direta (loja)"]
CONFIDENCE = ["Certeza", "Provável"]
YELLOW = PatternFill("solid", fgColor="FFF4B3")
GENERIC_DOMAINS = {"linkedin.com", "clutch.co", "theirstack.com", "glassdoor.com.br", "gupy.io", "github.com",
                   "goodfirms.co", "packagist.org", "google.com", "instagram.com", "facebook.com"}


def norm(name):
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"\b(ltda|s\.?a\.?|me|eireli|brasil|brazil|group|grupo|inc|digital)\b", "", s)
    return re.sub(r"[^a-z0-9]", "", s)


def domain(url):
    try:
        host = urlparse(url).netloc.lower()
    except ValueError:
        return None
    host = host[4:] if host.startswith("www.") else host
    parts = host.split(".")
    base = ".".join(parts[-3:]) if len(parts) >= 3 and parts[-2] in ("com", "net", "org") else ".".join(parts[-2:])
    return None if not base or base in GENERIC_DOMAINS else base


def split_list(value):
    return [x.strip() for x in (value or "").split(";") if x.strip()]


def clean(rows, exclude, former):
    excl = {norm(x) for x in exclude}
    former_n = {norm(x): x for x in former}
    seen_names, seen_domains = set(), set()
    out, rejected = [], []
    for r in rows:
        site = str(r.get("site") or "").strip()
        r = {k: (str(r.get(k) or "").strip()) for k in KEYS}
        if not r["empresa"]:
            continue
        n = norm(r["empresa"])
        if not r["fonte"].startswith("http") or not r["evidencia"]:
            rejected.append((r["empresa"], "sem fonte (link) ou evidência"))
            continue
        if n in excl or any(e and (e in n or n in e) for e in excl):
            rejected.append((r["empresa"], "empresa excluída"))
            continue
        d = domain(site) if site else None
        if n in seen_names or (d and d in seen_domains):
            rejected.append((r["empresa"], "duplicada"))
            continue
        seen_names.add(n)
        if d:
            seen_domains.add(d)
        if r["confianca"] not in CONFIDENCE:
            r["confianca"] = "Provável"
        if any(f and (f in n or n in f) for f in former_n):
            if "ex-empregador" not in r["observacao"].lower():
                r["observacao"] = ("Ex-empregador. " + r["observacao"]).strip()
        out.append(r)
    return out, rejected


def build(rows, output, title):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Empresas"
    ws.append(HEADER)
    for c in ws[1]:
        c.font = Font(bold=True)
    for i, r in enumerate(rows, 1):
        ws.append([i] + [r[k] for k in KEYS])
        if r["confianca"] == "Provável":
            for c in ws[ws.max_row]:
                c.fill = YELLOW
        for c in ws[ws.max_row]:
            c.alignment = Alignment(wrap_text=True, vertical="top")
        link = ws.cell(row=ws.max_row, column=9)
        link.hyperlink = r["fonte"]
    widths = [5, 30, 28, 18, 50, 11, 24, 30, 45]
    for col, w in zip("ABCDEFGHI", widths):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "C2"

    rs = wb.create_sheet("Resumo")
    rs.append([f"Resumo da pesquisa: {title}", None])
    rs.append([None, None])
    blocks = [("Tipo", "C", sorted({r["tipo"] for r in rows}, key=lambda t: (t not in TYPES, TYPES.index(t) if t in TYPES else 0, t))),
              ("Confiança", "F", CONFIDENCE),
              ("Serve para", "G", SERVE)]
    for label, col, values in blocks:
        rs.append([label, "Qtde"])
        rs[rs.max_row][0].font = rs[rs.max_row][1].font = Font(bold=True)
        first = rs.max_row + 1
        for v in values:
            row = rs.max_row + 1
            rs.append([v, f"=COUNTIF(Empresas!${col}:${col},A{row})"])
        if label == "Tipo":
            rs.append(["Total", f"=SUM(B{first}:B{rs.max_row})"])
        rs.append([None, None])
    rs.append(["Legenda", None])
    rs[rs.max_row][0].font = Font(bold=True)
    rs.append(["Certeza = evidência direta e atual (vaga, site, case, diretório oficial).", None])
    rs.append(["Provável = evidência antiga ou indireta (linha em amarelo); confirmar antes de abordar.", None])
    rs.append(["Vaga = empresa contrata devs da tecnologia. Parceria white-label = agência que pode terceirizar demanda. "
               "Prospecção direta = loja que usa a tecnologia e pode precisar de freela.", None])
    rs.column_dimensions["A"].width = 60
    wb.save(output)


def ensure_progress(root):
    path = root / "controle" / "progresso.json"
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    cv = read_profile_fields(root / "perfil.local.md").get("curriculo_base", "")
    write_json_atomic(path, {"curriculo_base": cv, "data_corte": None, "empresas": [], "historico": []})
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the company spreadsheet")
    ap.add_argument("entrada")
    ap.add_argument("saida")
    ap.add_argument("--excluir", default="")
    ap.add_argument("--ex-empregadores", default="")
    ap.add_argument("--limite", type=int)
    ap.add_argument("--titulo", default="")
    args = ap.parse_args(argv)
    rows = json.loads(Path(args.entrada).read_text(encoding="utf-8"))
    kept, rejected = clean(rows, split_list(args.excluir), split_list(args.ex_empregadores))
    if args.limite:
        kept = kept[: args.limite]
    if not kept:
        print("Nenhuma empresa válida."); return 1
    root = project_root()
    build(kept, root / args.saida if not Path(args.saida).is_absolute() else args.saida, args.titulo)
    created = ensure_progress(root)
    print(f"{len(kept)} empresas gravadas em {args.saida}")
    for name, why in rejected:
        print(f"  fora: {name} ({why})")
    print("controle/progresso.json criado" if created else "controle/progresso.json já existia (não mexi)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
