#!/usr/bin/env python3
"""Migrate controle/progresso.json and relatorio-final.xlsx to the new status format.

- The date leaves the status text: "PULADA_PELO_X (10/11/2026)" -> status "PULADA_PELO_CANDIDATO",
  data "2026-11-10". Entries without a date in the text get data = date of `atualizado_em`.
- Legacy names are renamed (PULADA_PELO_* -> PULADA_PELO_CANDIDATO, DESISTENCIA_DO_* ->
  DESISTENCIA_DO_CANDIDATO, etc.).
- The spreadsheet gets a "Data do status" column and the header "Pendências do candidato".
- Optionally sets progresso.json > data_corte (--data-corte YYYY-MM-DD).

Before writing, it prints the count per status before (normalized) and after. If they do not
match, NOTHING is written and the script exits with code 1. Backups are written to
controle/backup-migracao-<timestamp>/ before any change. Safe to run more than once.

Usage: python3 scripts/migrar_status.py [--data-corte YYYY-MM-DD] [--dry-run]
"""
import argparse
import collections
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

import openpyxl
from openpyxl.styles import Font

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import OFFICIAL_STATUSES, project_root, save_workbook_atomic, split_status, write_json_atomic  # noqa: E402

LEGACY_PENDING_PREFIX = "Pendências do "  # legacy header: "Pendências do <name>"
NEW_PENDING_HEADER = "Pendências do candidato"
DATE_HEADER = "Data do status"


def counts(values):
    return collections.Counter(v for v in values if v)


def show(title, counter):
    print(f"  {title}:")
    for k, v in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"    {v:3d}  {k}")
    print(f"    {sum(counter.values()):3d}  TOTAL")


def migrate_progress(prog):
    raw = [e.get("status") for e in prog["empresas"]]
    before = counts(split_status(s)[0] for s in raw)
    for e in prog["empresas"]:
        status, date_in_text = split_status(e.get("status"))
        e["status"] = status
        e["data"] = e.get("data") or date_in_text or str(e.get("atualizado_em", ""))[:10] or None
    after = counts(e["status"] for e in prog["empresas"])
    return raw, before, after


def migrate_sheet(ws, dates_by_num):
    header = [c.value for c in ws[1]]
    while header and header[-1] is None:
        header.pop()
    if "Status" not in header:
        sys.exit("relatorio-final.xlsx has no Status column")
    s_col = header.index("Status") + 1
    for i, h in enumerate(header):
        if h and str(h).startswith(LEGACY_PENDING_PREFIX) and h != NEW_PENDING_HEADER:
            ws.cell(row=1, column=i + 1, value=NEW_PENDING_HEADER)
    if DATE_HEADER in header:
        d_col = header.index(DATE_HEADER) + 1
    else:
        d_col = len(header) + 1
        ws.cell(row=1, column=d_col, value=DATE_HEADER).font = Font(bold=True)
    raw, new = [], []
    for row in ws.iter_rows(min_row=2):
        num = row[0].value
        cell = ws.cell(row=row[0].row, column=s_col)
        if num is None or not cell.value:
            continue
        raw.append(cell.value)
        status, date_in_text = split_status(cell.value)
        cell.value = status
        current = ws.cell(row=row[0].row, column=d_col).value
        ws.cell(row=row[0].row, column=d_col, value=current or date_in_text or dates_by_num.get(int(num)))
        new.append(status)
    return raw, counts(split_status(s)[0] for s in raw), counts(new)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Migrate statuses to the new format")
    ap.add_argument("--data-corte", help="set progresso.json > data_corte (YYYY-MM-DD)")
    ap.add_argument("--dry-run", action="store_true", help="only show the counts")
    args = ap.parse_args(argv)
    if args.data_corte:
        datetime.strptime(args.data_corte, "%Y-%m-%d")

    root = project_root()
    prog_path = root / "controle" / "progresso.json"
    xlsx_path = root / "relatorio-final.xlsx"
    prog = json.loads(prog_path.read_text(encoding="utf-8"))

    ok = True
    print("progresso.json")
    raw, before, after = migrate_progress(prog)
    show("antes (bruto)", counts(raw))
    show("antes (normalizado)", before)
    show("depois", after)
    if before != after or sum(counts(raw).values()) != sum(after.values()):
        print("  ERRO: contagens não batem"); ok = False
    invalid = [s for s in after if s not in OFFICIAL_STATUSES]
    if invalid:
        print(f"  ERRO: status fora da lista oficial: {invalid}"); ok = False

    wb = None
    if xlsx_path.exists():
        wb = openpyxl.load_workbook(xlsx_path)
        dates = {int(e["numero"]): e["data"] for e in prog["empresas"]}
        print("relatorio-final.xlsx")
        xraw, xb, xa = migrate_sheet(wb["Empresas"], dates)
        show("antes (bruto)", counts(xraw))
        show("antes (normalizado)", xb)
        show("depois", xa)
        if xb != xa or sum(counts(xraw).values()) != sum(xa.values()):
            print("  ERRO: contagens não batem"); ok = False
        if xa != after:
            print("  ERRO: planilha e progresso.json têm contagens diferentes"); ok = False

    if args.data_corte:
        prog["data_corte"] = args.data_corte
    else:
        prog.setdefault("data_corte", None)
    print(f"data_corte: {prog.get('data_corte')}")

    if not ok:
        print("NADA FOI GRAVADO.")
        return 1
    if args.dry_run:
        print("dry-run: nada foi gravado.")
        return 0

    backup = root / "controle" / f"backup-migracao-{datetime.now():%Y%m%d-%H%M%S}"
    backup.mkdir(parents=True)
    shutil.copy2(prog_path, backup / prog_path.name)
    if wb is not None:
        shutil.copy2(xlsx_path, backup / xlsx_path.name)
        save_workbook_atomic(wb, xlsx_path)
    write_json_atomic(prog_path, prog)
    print(f"Gravado. Backup em {backup.relative_to(root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
