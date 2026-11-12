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
import re
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import unquote

import openpyxl
from openpyxl.styles import Alignment, Font

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (DO_NOT_CONTACT, OFFICIAL_STATUSES, backup_file, find_company_sheet,  # noqa: E402
                    mentions_person, normalize_url, normalize_url_text, project_root, read_profile_fields,
                    save_workbook_atomic, split_status, write_json_atomic)

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


# ---------------------------------------------------------------------------------------------
# "Feito" in the panel: the candidate's click is the source of truth.
# mark_done() records an item of the "Pendentes" tab as ENVIADO (sent) today in every place the
# robot records a send: progresso.json > historico, relatorio-parcial.md (sections 3/4), the
# company report (relatorios/NNN-*.md), the draft file, controle/historico-contatos.md and the
# relatorio-final.xlsx row. Every write is a reversible operation stored in
# controle/painel-feitos.json, so undo_done() reverts exactly what was written.
# ---------------------------------------------------------------------------------------------
DONE_LOG = Path("controle") / "painel-feitos.json"


def load_done(root):
    path = Path(root) / DONE_LOG
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"feitos": []}


def done_ids(root):
    return {f["id"] for f in load_done(root).get("feitos", [])}


def _read(path):
    return path.read_text(encoding="utf-8") if path.exists() else None


def _write(path, text):
    path.write_text(text, encoding="utf-8", newline="")


def _lines(text):
    return text.split("\n")


def _replace_line(root, rel, old, new, ops):
    path = Path(root) / rel
    text = _read(path)
    if text is None or old not in _lines(text):
        return False
    lines = _lines(text)
    lines[lines.index(old)] = new
    _write(path, "\n".join(lines))
    ops.append({"op": "trocar_linha", "arquivo": rel, "antes": old, "depois": new})
    return True


def _insert_line(root, rel, index, line, ops):
    """Insert `line` before line number `index` (None = at the end of the file)."""
    path = Path(root) / rel
    text = _read(path)
    if text is None:
        return False
    lines = _lines(text)
    if index is None:
        while lines and lines[-1] == "":
            lines.pop()
        lines += [line, ""]
    else:
        lines.insert(index, line)
    _write(path, "\n".join(lines))
    ops.append({"op": "inserir_linha", "arquivo": rel, "linha": line})
    return True


def _company_report(root, num):
    folder = Path(root) / "relatorios"
    if num is None or not folder.exists():
        return None
    found = sorted(folder.glob(f"{int(num):03d}-*.md")) or sorted(folder.glob(f"{int(num)}-*.md"))
    return found[0].relative_to(root).as_posix() if found else None


def _contacts_insert_index(text, num):
    """Line index right after the '### #N ...' block of historico-contatos.md (None = end of file)."""
    lines = _lines(text)
    start = next((i for i, l in enumerate(lines) if re.match(rf"^###\s+#{int(num)}\b", l)), None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("#")), len(lines))
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1
    return end


def _xlsx_append(root, num, column, suffix, ops):
    path = Path(root) / "relatorio-final.xlsx"
    if num is None or not path.exists():
        return False
    wb = openpyxl.load_workbook(path)
    ws = wb["Empresas"]
    header = [c.value for c in ws[1]]
    if column not in header:
        return False
    col = header.index(column) + 1
    row = next((r for r in ws.iter_rows(min_row=2) if r[0].value is not None and str(r[0].value).split(".")[0] == str(int(num))), None)
    if row is None:
        return False
    cell = ws.cell(row=row[0].row, column=col)
    cell.value = f"{cell.value or ''}{suffix}"
    save_workbook_atomic(wb, path)
    ops.append({"op": "xlsx_sufixo", "numero": int(num), "coluna": column, "sufixo": suffix})
    return True


def _history(root, note, ops):
    path = Path(root) / "controle" / "progresso.json"
    if not path.exists():
        return False
    prog = json.loads(path.read_text(encoding="utf-8"))
    entry = {"em": date.today().isoformat(), "nota": note}
    prog.setdefault("historico", []).append(entry)
    backup_file(path)
    write_json_atomic(path, prog)
    ops.append({"op": "historico", "em": entry["em"], "nota": note})
    return True


def _section_row(text, section_no, predicate):
    """First table line of '## <section_no>.' in relatorio-parcial.md for which predicate(line) is true."""
    inside = False
    for line in _lines(text):
        if line.startswith("## "):
            inside = line.startswith(f"## {section_no}.")
            continue
        if inside and line.strip().startswith("|") and predicate(line):
            return line
    return None


def _mark_row(line, first_cell=None, prefix_cell=None):
    """Rewrite a markdown table row: replace cell 0 and/or prefix another cell."""
    cells = re.split(r"(?<!\\)\|", line.strip().strip("|"))
    if first_cell is not None:
        cells[0] = f" {first_cell} "
    if prefix_cell is not None:
        idx, prefix = prefix_cell
        cells[idx] = f" {prefix} {cells[idx].strip()} "
    return "|" + "|".join(cells) + "|"


def _heading_of(text, url, name):
    """The '## N) ...' heading line of the person in a LinkedIn draft (by profile URL, then by name)."""
    lines = _lines(text)
    heads = [i for i, l in enumerate(lines) if re.match(r"^#{2,3}\s+\d+\)", l)]
    key = normalize_url(url)
    for n, i in enumerate(heads):
        end = heads[n + 1] if n + 1 < len(heads) else len(lines)
        for l in lines[i:end]:
            m = re.match(r"^-\s*(?:Perfil|P[áa]gina)\s*:\s*(\S+)", l.strip())
            if m and key and normalize_url(unquote(m.group(1))) == normalize_url(unquote(key)):
                return lines[i]
    for i in heads:
        if name and name.lower() in lines[i].lower():
            return lines[i]
    return None


def mark_done(root, kind, item, today=None):
    """Record one item of the panel as sent (or handled) today. Returns the journal entry."""
    root = Path(root)
    today = today or date.today().isoformat()
    log = load_done(root)
    if any(f["id"] == item["id"] for f in log["feitos"]):
        raise ValueError("already marked")
    br = f"{today[8:10]}/{today[5:7]}/{today[:4]}"
    ops = []
    nums = [n for n in (item.get("numeros") or [item.get("numero")]) if n is not None]
    company = item.get("empresa") or ""
    if kind == "linkedin":
        what = f"LinkedIn para {item.get('nome')}"
    elif kind == "email":
        what = f"e-mail para {item.get('para')} ({item.get('assunto')})"
    elif kind == "followup":
        what = f"follow-up para {item.get('quem')}"
    elif kind == "resposta":
        what = f"resposta tratada: {item.get('texto')}"
    elif kind == "decisao":
        what = f"decisão tomada: {item.get('motivo')}"
    else:
        raise ValueError(f"unknown kind {kind!r}")
    sent = "ENVIADO" if kind in ("linkedin", "email", "followup") else "FEITO"
    label = f"{sent} {br} (marcado no painel): {what}"

    parcial = root / "relatorio-parcial.md"
    text = _read(parcial)
    if text is not None and kind == "linkedin" and item.get("perfil"):
        key = normalize_url(unquote(item["perfil"]))
        pattern = re.compile(re.escape(key) + r"(?![\w%-])")
        row = _section_row(text, 4, lambda l: "✅" not in l and pattern.search(normalize_url_text(unquote(l).lower())))
        if row:
            _replace_line(root, "relatorio-parcial.md", row, _mark_row(row, "✅", (2, f"**ENVIADO {br}**")), ops)
    if text is not None and kind == "email" and item.get("para"):
        row = _section_row(text, 3, lambda l: "✅" not in l and item["para"].lower() in l.lower())
        if row:
            num = item.get("numero")
            _replace_line(root, "relatorio-parcial.md", row, _mark_row(row, f"{num} ✅ ENVIADO {br[:5]}"), ops)

    draft = item.get("arquivo")
    if draft and (root / draft).exists():
        dtext = _read(root / draft)
        if kind == "linkedin":
            head = _heading_of(dtext, item.get("perfil"), item.get("nome"))
            if head:
                new = re.sub(r"^(#{2,3}\s+\d+\)\s*)", rf"\1[ENVIADO {br}] ", head)
                _replace_line(root, draft, head, new, ops)
        elif kind == "email":
            _insert_line(root, draft, 0, f"> ✅ ENVIADO pelo candidato em {br} (marcado no painel). Não criar rascunho novo para este endereço.", ops)

    for num in nums:
        report = _company_report(root, num)
        if report:
            _insert_line(root, report, None, f"- {label}.", ops)
        contacts = root / "controle" / "historico-contatos.md"
        ctext = _read(contacts)
        if ctext is not None:
            _insert_line(root, "controle/historico-contatos.md", _contacts_insert_index(ctext, num),
                         f"- (painel) {br}: {sent} pelo candidato, {what} (#{num} {company}).".replace("  ", " "), ops)
        column = "Rascunhos criados" if kind in ("linkedin", "email") else "Pendências do candidato"
        _xlsx_append(root, num, column, f" | {label}.", ops)
    _history(root, f"Painel: {label} (#{', #'.join(str(n) for n in nums)}).", ops)

    entry = {"id": item["id"], "tipo": kind, "data": today, "descricao": what, "empresa": company,
             "numero": nums[0] if nums else None, "operacoes": ops}
    log["feitos"].append(entry)
    path = root / DONE_LOG
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(path, log)
    return entry


def undo_done(root, item_id):
    """Revert every write of mark_done() for this item. Returns a list of warnings (empty = all reverted)."""
    root = Path(root)
    log = load_done(root)
    entry = next((f for f in log["feitos"] if f["id"] == item_id), None)
    if entry is None:
        raise KeyError(item_id)
    warnings = []
    for op in reversed(entry["operacoes"]):
        if op["op"] == "trocar_linha":
            ok = _replace_line(root, op["arquivo"], op["depois"], op["antes"], [])
        elif op["op"] == "inserir_linha":
            path = root / op["arquivo"]
            text = _read(path)
            ok = text is not None and op["linha"] in _lines(text)
            if ok:
                lines = _lines(text)
                del lines[len(lines) - 1 - lines[::-1].index(op["linha"])]
                _write(path, "\n".join(lines))
        elif op["op"] == "xlsx_sufixo":
            path = root / "relatorio-final.xlsx"
            ok = False
            if path.exists():
                wb = openpyxl.load_workbook(path)
                ws = wb["Empresas"]
                header = [c.value for c in ws[1]]
                row = next((r for r in ws.iter_rows(min_row=2) if r[0].value is not None
                            and str(r[0].value).split(".")[0] == str(op["numero"])), None)
                if row is not None and op["coluna"] in header:
                    cell = ws.cell(row=row[0].row, column=header.index(op["coluna"]) + 1)
                    if str(cell.value or "").endswith(op["sufixo"]):
                        rest = str(cell.value)[: -len(op["sufixo"])]
                        cell.value = rest or None
                        save_workbook_atomic(wb, path)
                        ok = True
        elif op["op"] == "historico":
            path = root / "controle" / "progresso.json"
            prog = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            hist = prog.get("historico", [])
            idx = next((i for i in range(len(hist) - 1, -1, -1)
                        if hist[i].get("nota") == op["nota"] and hist[i].get("em") == op["em"]), None)
            ok = idx is not None
            if ok:
                del hist[idx]
                backup_file(path)
                write_json_atomic(path, prog)
        else:
            ok = False
        if not ok:
            warnings.append(f"{op['op']} {op.get('arquivo') or op.get('coluna') or ''}: não encontrei o que desfazer")
    log["feitos"] = [f for f in log["feitos"] if f["id"] != item_id]
    write_json_atomic(root / DONE_LOG, log)
    return warnings


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
