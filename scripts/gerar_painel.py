#!/usr/bin/env python3
"""Build painel/data.json (and painel/data.js) from the project files.

Reads: controle/progresso.json, relatorios/rodada-*.md, relatorio-final.xlsx (or the company sheet).
Writes: painel/data.json and painel/data.js (same data as `window.PAINEL_DATA = ...`, so the
panel also works when opened straight from disk, as a file:// page).
Both outputs are personal data and are gitignored.

Usage (from the project folder; on Windows use `py -3` instead of `python3`):
  python3 scripts/gerar_painel.py             build painel/data.json and open painel/index.html in the browser
  python3 scripts/gerar_painel.py --no-open   build painel/data.json only (does not open the browser)
  python3 scripts/gerar_painel.py --demo      copy the panel + painel/demo-data.json to docs/demo/ (GitHub Pages)
"""
import collections
import json
import re
import sys
import webbrowser
from datetime import datetime
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import find_company_sheet, project_root, split_status  # noqa: E402

STATUS_ORDER = [
    "CANDIDATURA_ENVIADA", "RASCUNHOS_CRIADOS", "VAGA_GESTAO_PARA_O_CANDIDATO_DECIDIR",
    "JA_CONTATADA_SEM_NOVA_ACAO", "SEM_OPORTUNIDADE", "NAO_ELEGIVEL", "PULADA_PELO_CANDIDATO",
    "DESISTENCIA_DO_CANDIDATO", "PRECISA_DO_CANDIDATO", "AGUARDANDO_RESPOSTA_CANDIDATO", "ERRO",
]
PENDING = "FALTA_PROCESSAR"


def _round_sort_key(path):
    m = re.search(r"rodada-(\d{4}-\d{2}-\d{2})(?:-(\d+))?", path.name)
    return (m.group(1), int(m.group(2) or 1)) if m else ("", 0)


def section(text, title_prefix):
    """Return the body of the '## <title_prefix...>' section (until the next '## ')."""
    m = re.search(rf"^## {re.escape(title_prefix)}[^\n]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


def table_rows(body):
    rows = []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("|") or re.match(r"^\|[\s:|-]+\|$", line):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        rows.append(cells)
    return rows[1:] if rows else []  # drop header


def followup_label(entry):
    """'Recrutadora Exemplo (Loja Exemplo 1, #21)' on 2026-11-12 -> '12/11 — Loja Exemplo 1 (#21)'.

    Every '(<company>, #N)' or '<company> (#N)' found in `quem` becomes 'Company (#N)'; several are
    joined with ' e '. Without any '#N' the text is kept as it is.
    """
    parts = []
    for m in re.finditer(r"([^()]*?)\s*\(([^()]*?)#\s*(\d+)\s*\)", entry["quem"]):
        before, inner, num = m.group(1), m.group(2).strip().rstrip(","), m.group(3)
        company = inner.strip() or re.sub(r"^(e|and|,)\s+", "", before.strip()).strip()
        parts.append(f"{company} (#{num})")
    label = " e ".join(parts) if parts else entry["quem"]
    y, mo, d = entry["data"].split("-")
    return f"{d}/{mo} — {label}"


def todo_items(raw):
    """Turn parsed to-do items into {texto, subitens}.

    An item whose own lines are follow-ups ("Follow-ups ...:" + "- X: a partir de DD/MM/AAAA") shows them
    as sub-items in the 'DD/MM — Empresa (#N)' format; if it has none, the item is dropped.
    """
    items = []
    for it in raw:
        subs = [followup_label(f) for f in it["followups"]]
        is_followup_header = bool(it["followups"]) or re.match(r"(?i)^follow-?ups?\b", it["texto"])
        if is_followup_header and not subs:
            continue
        items.append({"texto": it["texto"], "subitens": subs})
    return items


def parse_round(path):
    text = path.read_text(encoding="utf-8")
    title = text.splitlines()[0].lstrip("# ").strip() if text else path.stem
    m = re.search(r"(\d{4}-\d{2}-\d{2})", path.name)
    info = {"arquivo": f"relatorios/{path.name}", "titulo": title, "data": m.group(1) if m else None}

    companies = []
    for cells in table_rows(section(text, "Empresa por empresa")):
        if len(cells) < 3 or not cells[0].strip("#").isdigit():
            continue
        status, _ = split_status(cells[2])
        companies.append({"numero": int(cells[0].strip("#")), "empresa": cells[1], "status": status,
                          "motivo": cells[3] if len(cells) > 3 else "", "rascunhos": 0})

    by_num = {c["numero"]: c for c in companies}
    li_rows = table_rows(section(text, "Rascunhos novos de LinkedIn"))
    em_rows = table_rows(section(text, "Rascunhos novos de e-mail"))
    for rows, col in ((li_rows, 1), (em_rows, 0)):
        for cells in rows:
            if len(cells) > col:
                num = cells[col].strip("# ✅").split()[0] if cells[col].strip() else ""
                if num.isdigit() and int(num) in by_num:
                    by_num[int(num)]["rascunhos"] += 1

    summary = section(text, "Resumo")
    drafts = re.search(r"Rascunhos novos:\**\s*(\d+)\s*e-mails?.*?(\d+)\s*mensage", summary, re.S)
    apps = re.search(r"Candidaturas enviadas:\**\s*(\d+)", summary)
    info["rascunhos_novos"] = {"email": int(drafts.group(1)) if drafts else len(em_rows),
                               "linkedin": int(drafts.group(2)) if drafts else len(li_rows)}
    info["candidaturas"] = int(apps.group(1)) if apps else 0
    info["empresas"] = companies
    info["status"] = dict(collections.Counter(c["status"] for c in companies if c["status"]))

    todo_body = section(text, "O que depende")
    todo, followups = [], []
    current = None
    for line in todo_body.splitlines():
        fu = re.match(r"^\s*[-*]\s+(.+?):\s*a partir de\s+(\d{2})/(\d{2})/(\d{4})", line)
        if fu:
            entry = {"quem": fu.group(1).strip(), "data": f"{fu.group(4)}-{fu.group(3)}-{fu.group(2)}"}
            followups.append(entry)
            if current is not None:
                current["followups"].append(entry)
            continue
        item = re.match(r"^\d+\.\s+(.*)", line.strip())
        if item:
            current = {"texto": re.sub(r"\*\*", "", item.group(1)).strip(), "followups": []}
            todo.append(current)
    info["o_que_fazer"] = todo_items(todo)
    info["followups"] = followups

    replied = []
    for line in section(text, "Envios que encontrei").splitlines():
        m = re.match(r"^\s*-\s*Responderam[^:]*:\s*(.*)", line)
        if m:
            replied += [p.strip(" .") for p in re.split(r";\s*", m.group(1)) if p.strip(" .")]
    info["responderam"] = replied
    return info


def company_types(root, statuses):
    path = root / "relatorio-final.xlsx"
    if not path.exists():
        path = find_company_sheet(root)
    if not path or not Path(path).exists():
        return [], 0
    ws = openpyxl.load_workbook(path, read_only=True)["Empresas"]
    rows = ws.iter_rows(values_only=True)
    header = list(next(rows))
    t_idx = header.index("Tipo") if "Tipo" in header else None
    total = 0
    types = collections.OrderedDict()
    for r in rows:
        if not r or r[0] is None:
            continue
        total += 1
        tipo = (r[t_idx] if t_idx is not None else None) or "Sem tipo"
        entry = types.setdefault(tipo, {"tipo": tipo, "total": 0, "concluidas": 0})
        entry["total"] += 1
        try:
            if int(r[0]) in statuses:
                entry["concluidas"] += 1
        except (TypeError, ValueError):
            pass
    return sorted(types.values(), key=lambda t: -t["total"]), total


def build(root):
    prog_path = root / "controle" / "progresso.json"
    prog = json.loads(prog_path.read_text(encoding="utf-8")) if prog_path.exists() else {"empresas": [], "historico": []}
    statuses = {}
    per_day = collections.Counter()
    for e in prog.get("empresas", []):
        status, _ = split_status(e.get("status"))
        statuses[int(e["numero"])] = status
        day = str(e.get("atualizado_em") or e.get("data") or "")[:10]
        if day:
            per_day[day] += 1

    types, total = company_types(root, statuses)
    total = max(total, len(statuses))
    funnel_counts = collections.Counter(statuses.values())
    funnel = [{"status": s, "total": funnel_counts[s]} for s in STATUS_ORDER if funnel_counts.get(s)]
    funnel += [{"status": s, "total": n} for s, n in funnel_counts.items() if s not in STATUS_ORDER]
    if total - len(statuses) > 0:
        funnel.append({"status": PENDING, "total": total - len(statuses)})

    rounds = sorted((root / "relatorios").glob("rodada-*.md"), key=_round_sort_key) if (root / "relatorios").exists() else []
    latest = parse_round(rounds[-1]) if rounds else None
    replied, followups = [], []
    for r in rounds[-3:]:
        parsed = parse_round(r)
        replied += [{"texto": t, "rodada": parsed["data"]} for t in parsed["responderam"]]
    if latest:
        followups = sorted(latest["followups"], key=lambda f: f["data"])

    return {
        "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "demo": False,
        "projeto": {"total": total, "concluidas": len(statuses), "faltam": max(total - len(statuses), 0),
                    "data_corte": prog.get("data_corte")},
        "rodada": latest,
        "funil": funnel,
        "por_tipo": types,
        "rodadas": [{"data": d, "empresas": n} for d, n in sorted(per_day.items())],
        "responderam": list(reversed(replied)),
        "followups": followups,
    }


def build_demo():
    repo = Path(__file__).resolve().parent.parent
    html = (repo / "painel" / "index.html").read_text(encoding="utf-8")
    html = html.replace('<meta name="painel-data" content="data.json">', '<meta name="painel-data" content="demo-data.json">')
    html = html.replace('<script src="data.js" onerror="void 0"></script>\n', "")
    out = repo / "docs" / "demo"
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(html, encoding="utf-8")
    (out / "demo-data.json").write_text((repo / "painel" / "demo-data.json").read_text(encoding="utf-8"), encoding="utf-8")
    print("docs/demo/index.html + docs/demo/demo-data.json")


def open_panel(index_html):
    """Open the panel in the default browser (macOS, Linux and Windows). Returns True if it opened."""
    try:
        return bool(webbrowser.open(Path(index_html).resolve().as_uri()))
    except webbrowser.Error:
        return False


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if "--demo" in args:
        build_demo()
        return
    root = project_root()
    data = build(root)
    out = root / "painel"
    out.mkdir(exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    (out / "data.json").write_text(payload + "\n", encoding="utf-8")
    (out / "data.js").write_text(f"window.PAINEL_DATA = {payload};\n", encoding="utf-8")
    p = data["projeto"]
    print(f"painel/data.json: {p['concluidas']} de {p['total']} empresas; "
          f"rodada: {data['rodada']['arquivo'] if data['rodada'] else 'nenhuma'}")
    if "--no-open" in args:
        return
    index_html = out / "index.html"
    if index_html.exists() and open_panel(index_html):
        print("Painel aberto no navegador: painel/index.html")
    else:
        print(f"Abra no navegador: {index_html.resolve().as_uri()}")


if __name__ == "__main__":
    main()
