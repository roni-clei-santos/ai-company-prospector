#!/usr/bin/env python3
"""Record a finished company in controle/progresso.json AND relatorio-final.xlsx (always both).

Usage (run from the project folder):
  python3 scripts/registrar.py <company.json>
  python3 scripts/registrar.py --data-corte 2026-11-09
  python3 scripts/registrar.py --historico "note text" [--sessao N]
  python3 scripts/registrar.py --nao-contatar "Full Name" [--empresa X] [--email E] [--linkedin URL] [--motivo M]

company.json keys: numero, empresa, status, data (optional, ISO; default today) and the report
columns: contato_anterior, canais, vagas, candidaturas, rascunhos, motivo, pendencias, evidencias.
The status must be one of the official names (PROMPT section 12). A date written inside the
status text, e.g. "PULADA_PELO_CANDIDATO (10/11/2026)", is moved to the `data` field.

NAO_CONTATAR: a company with this status is never changed to another status (and never gets a new
draft) unless --forcar is given. --nao-contatar adds a PERSON to progresso.json > nao_contatar.
"""
import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (DO_NOT_CONTACT, OFFICIAL_STATUSES, backup_file, find_company_sheet,  # noqa: E402
                    mentions_person, normalize_url, project_root, read_profile_fields, save_workbook_atomic, split_status, write_json_atomic)

# (json key, column header, accepted legacy header prefixes)
COLUMNS = [
    ("status", "Status", []),
    ("contato_anterior", "Contato anterior", []),
    ("canais", "Canais encontrados", []),
    ("vagas", "Vagas avaliadas", []),
    ("candidaturas", "Candidaturas enviadas", []),
    ("rascunhos", "Rascunhos criados", []),
    ("motivo", "Motivo", []),
    ("pendencias", "Pendências do candidato", ["Pendências do "]),  # legacy: "Pendências do <name>"
    ("evidencias", "Evidências", []),
    ("data", "Data do status", []),
]


def paths():
    root = project_root()
    return root, root / "relatorio-final.xlsx", root / "controle" / "progresso.json"


def load_progress(progress_path):
    if progress_path.exists():
        return json.loads(progress_path.read_text(encoding="utf-8"))
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    cv = read_profile_fields().get("curriculo_base", "")
    return {"curriculo_base": cv, "data_corte": None, "empresas": [], "historico": []}


def load_output(output_path):
    if output_path.exists():
        return openpyxl.load_workbook(output_path)
    sheet = find_company_sheet()
    if sheet is None:
        sys.exit("Company spreadsheet not found (perfil.local.md > planilha_empresas or empresas-*.xlsx).")
    src = openpyxl.load_workbook(sheet)["Empresas"]
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Empresas"
    header = [c.value for c in src[1] if c.value is not None]
    ws.append(header + [h for _, h, _ in COLUMNS])
    for row in src.iter_rows(min_row=2, values_only=True):
        if row[0] is None:
            continue
        vals = list(row[: len(header)])
        vals[0] = int(vals[0])
        ws.append(vals + [None] * len(COLUMNS))
    for c in ws[1]:
        c.font = Font(bold=True)
    ws.freeze_panes = "C2"
    return wb


def column_map(ws):
    """Map json key -> column index (1-based); appends missing columns at the end."""
    header = [c.value for c in ws[1]]
    while header and header[-1] is None:
        header.pop()
    result = {}
    for key, name, legacy in COLUMNS:
        idx = next((i for i, h in enumerate(header) if h == name), None)
        if idx is None:
            idx = next((i for i, h in enumerate(header) if any(str(h or '').startswith(p) for p in legacy)), None)
        if idx is None:
            header.append(name)
            idx = len(header) - 1
            cell = ws.cell(row=1, column=idx + 1, value=name)
            cell.font = Font(bold=True)
        result[key] = idx + 1
    return result


def record_company(data, force=False):
    _, output_path, progress_path = paths()
    num = int(data["numero"])
    status, date_in_text = split_status(data.get("status"))
    if status not in OFFICIAL_STATUSES:
        sys.exit(f"Invalid status {data.get('status')!r}. Allowed: {', '.join(OFFICIAL_STATUSES)}")
    if progress_path.exists() and not force:
        current = next((e for e in load_progress(progress_path)["empresas"] if int(e["numero"]) == num), None)
        if current and split_status(current.get("status"))[0] == DO_NOT_CONTACT and status != DO_NOT_CONTACT:
            sys.exit(f"#{num} is {DO_NOT_CONTACT}: not changed. Only the candidate can lift it (--forcar).")
    status_date = data.get("data") or date_in_text or date.today().isoformat()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    wb = load_output(output_path)
    ws = wb["Empresas"]
    cols = column_map(ws)
    target = next((r for r in ws.iter_rows(min_row=2) if r[0].value is not None and int(r[0].value) == num), None)
    if target is None:
        sys.exit(f"Row #{num} not found in relatorio-final.xlsx")
    values = dict(data, status=status, data=status_date)
    for key, _, _ in COLUMNS:
        cell = ws.cell(row=target[0].row, column=cols[key], value=values.get(key, ""))
        cell.alignment = Alignment(wrap_text=True, vertical="top")

    prog = load_progress(progress_path)
    prog["empresas"] = [e for e in prog["empresas"] if int(e["numero"]) != num]
    prog["empresas"].append({
        "numero": num, "empresa": data["empresa"], "status": status,
        "data": status_date, "atualizado_em": now,
    })
    prog["empresas"].sort(key=lambda e: int(e["numero"]))

    backup_file(progress_path)
    save_workbook_atomic(wb, output_path)
    write_json_atomic(progress_path, prog)
    print(f"#{num} {data['empresa']}: {status} ({status_date}) registrado")


def set_cutoff(value):
    datetime.strptime(value, "%Y-%m-%d")
    _, _, progress_path = paths()
    prog = load_progress(progress_path)
    prog["data_corte"] = value
    backup_file(progress_path)
    write_json_atomic(progress_path, prog)
    print(f"data_corte = {value}")


def add_history(note, session=None):
    _, _, progress_path = paths()
    prog = load_progress(progress_path)
    entry = {"em": date.today().isoformat(), "nota": note}
    if session:
        entry["sessao"] = str(session)
    prog.setdefault("historico", []).append(entry)
    backup_file(progress_path)
    write_json_atomic(progress_path, prog)
    print("historico +1")


def add_do_not_contact(name, company=None, email=None, linkedin=None, reason=None):
    """Add a person to progresso.json > nao_contatar (no duplicates by e-mail, LinkedIn or name+company)."""
    if not (name or email or linkedin):
        sys.exit("--nao-contatar needs a name, --email or --linkedin")
    _, _, progress_path = paths()
    prog = load_progress(progress_path)
    people = prog.setdefault("nao_contatar", [])
    entry = {k: v for k, v in {"nome": name, "empresa": company, "email": (email or "").strip().lower() or None,
                               "linkedin_url": normalize_url(linkedin) or None, "motivo": reason}.items() if v}
    probe = " ".join(str(entry.get(k, "")) for k in ("nome", "email", "linkedin_url"))
    for p in people:
        same_company = not company or not p.get("empresa") or p["empresa"].lower() == company.lower()
        if same_company and mentions_person(probe, p):
            print(f"{DO_NOT_CONTACT}: {p.get('nome') or p.get('email') or p.get('linkedin_url')} already listed")
            return
    entry["em"] = date.today().isoformat()
    people.append(entry)
    backup_file(progress_path)
    write_json_atomic(progress_path, prog)
    print(f"{DO_NOT_CONTACT}: {name or email or linkedin} registrado")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Record a company in progresso.json and relatorio-final.xlsx")
    ap.add_argument("arquivo", nargs="?", help="company JSON file")
    ap.add_argument("--data-corte", help="set progresso.json > data_corte (YYYY-MM-DD)")
    ap.add_argument("--historico", help="append a note to progresso.json > historico")
    ap.add_argument("--sessao", help="session number for --historico")
    ap.add_argument("--forcar", action="store_true", help="allow changing a company that is NAO_CONTATAR")
    ap.add_argument("--nao-contatar", metavar="NOME", help="add a person to progresso.json > nao_contatar")
    ap.add_argument("--empresa", help="company of the --nao-contatar person")
    ap.add_argument("--email", help="e-mail of the --nao-contatar person")
    ap.add_argument("--linkedin", help="LinkedIn URL of the --nao-contatar person")
    ap.add_argument("--motivo", help="reason for --nao-contatar")
    args = ap.parse_args(argv)
    person = args.nao_contatar or args.email or args.linkedin
    if not (args.arquivo or args.data_corte or args.historico or person):
        ap.error("nothing to do")
    if args.arquivo:
        record_company(json.loads(Path(args.arquivo).read_text(encoding="utf-8")), force=args.forcar)
    if person:
        add_do_not_contact(args.nao_contatar, args.empresa, args.email, args.linkedin, args.motivo)
    if args.data_corte:
        set_cutoff(args.data_corte)
    if args.historico:
        add_history(args.historico, args.sessao)


if __name__ == "__main__":
    main()
