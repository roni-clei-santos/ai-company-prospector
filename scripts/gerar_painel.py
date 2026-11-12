#!/usr/bin/env python3
"""Build painel/data.json (and painel/data.js) from the project files.

Reads: controle/progresso.json, relatorios/rodada-*.md, relatorio-final.xlsx (or the company sheet),
relatorio-parcial.md (sections 2, 3 and 4) and the drafts in rascunhos/linkedin/ and rascunhos/email/
(for the "Pendentes" tab: everything the candidate still has to send or decide, from every round).
Writes: painel/data.json and painel/data.js (same data as `window.PAINEL_DATA = ...`, so the
panel also opens straight from disk, as a file:// page, read-only).
Both outputs are personal data and are gitignored.

By default the panel opens through the local server (scripts/servidor_painel.py, only on
http://127.0.0.1, standard library only), started in the background or reused if it is already
running for this project. Through the server, the "Feito" buttons record the item as sent.

Usage (from the project folder; on Windows use `py -3` instead of `python3`):
  python3 scripts/gerar_painel.py             build the data, start the local server and open the panel
  python3 scripts/gerar_painel.py --no-open   build painel/data.json only (no server, no browser)
  python3 scripts/gerar_painel.py --arquivo   build and open painel/index.html from disk (read-only)
  python3 scripts/gerar_painel.py --demo      copy the panel + painel/demo-data.json to docs/demo/ (GitHub Pages)
"""
import collections
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import webbrowser
from datetime import date, datetime
from pathlib import Path
from urllib.parse import unquote

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (DO_NOT_CONTACT, _fold, do_not_contact, find_company_sheet, mentions_person,  # noqa: E402
                    normalize_url, project_root, read_profile_fields, split_status)

GMAIL_DRAFTS = "https://mail.google.com/mail/u/0/#drafts"

STATUS_ORDER = [
    "CANDIDATURA_ENVIADA", "RASCUNHOS_CRIADOS", "VAGA_GESTAO_PARA_O_CANDIDATO_DECIDIR",
    "JA_CONTATADA_SEM_NOVA_ACAO", "SEM_OPORTUNIDADE", "NAO_ELEGIVEL", "PULADA_PELO_CANDIDATO",
    "DESISTENCIA_DO_CANDIDATO", "PRECISA_DO_CANDIDATO", "AGUARDANDO_RESPOSTA_CANDIDATO", "ERRO",
    "NAO_CONTATAR",
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


# ---------------------------------------------------------------------------------------------
# "Pendentes" tab: everything the candidate still has to send or decide, from every round.
# Sources: relatorio-parcial.md (section 2 = decisions, 3 = e-mails, 4 = LinkedIn), the drafts in
# rascunhos/, progresso.json (statuses and NAO_CONTATAR) and every relatorios/rodada-*.md.
# ---------------------------------------------------------------------------------------------
SENT_MARK = "✅"
BLOCKED = re.compile(r"N[ÃA]O\s+ENVIAR", re.I)
URL = re.compile(r"https?://[^\s)>\]|,;\"']+")
# a to-do item that leaves a job application to the candidate
DECISION = re.compile(r"decis[ãa]o [ée] sua|voc[êe] decide|quer se candidatar|decidir se|se quiser tentar"
                      r"|para (?:voc[êe]|o candidato) decidir", re.I)
# a reply that asks something of the candidate ... unless the report says it was already handled
ACTION = re.compile(r"\b(pediu|pede|pedindo|perguntou|pergunta|quer saber|solicitou|aguarda|espera|convidou"
                    r"|marcar|agendar|entrevista|ligar)\b", re.I)
HANDLED = re.compile(r"voc[êe] (?:já )?(?:respondeu|mandou|enviou)|j[áa] (?:respond|mand|envi)", re.I)
DECIDED = {"DESISTENCIA_DO_CANDIDATO", "PULADA_PELO_CANDIDATO", DO_NOT_CONTACT}


def table(body):
    """Markdown table -> (header cells, [(cells, raw line), ...]). An escaped '\\|' stays inside its cell."""
    header, rows = None, []
    for line in body.splitlines():
        s = line.strip()
        if not s.startswith("|") or re.match(r"^\|[\s:|-]+\|$", s):
            continue
        cells = [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", s.strip().strip("|"))]
        if header is None:
            header = cells
        else:
            rows.append((cells, s))
    return header or [], rows


def _col(header, *names, default=None):
    for i, h in enumerate(header):
        if any(_fold(h).startswith(n) for n in names):
            return i
    return default


def is_pending_row(line):
    """A row of sections 3/4 is pending when it has no ✅ and no 'NÃO ENVIAR'."""
    return SENT_MARK not in line and not BLOCKED.search(line)


def count_linkedin_section4(parcial_text):
    """Official pending count: people in section 4 of relatorio-parcial.md without ✅ and without 'NÃO ENVIAR'."""
    _, rows = table(section(parcial_text, "4."))
    return sum(1 for cells, line in rows if len(cells) >= 3 and is_pending_row(line))


def section4_pending_names(parcial_text):
    """Names of the pending people in section 4 (same rule as count_linkedin_section4)."""
    _, rows = table(section(parcial_text, "4."))
    return [split_recipient(cells[2])[0] for cells, line in rows if len(cells) >= 3 and is_pending_row(line)]


def _number(text):
    m = re.search(r"#?\s*(\d+)", text or "")
    return int(m.group(1)) if m else None


def draft_blocks(text):
    """Person blocks of a rascunhos/linkedin/*.md file: one per '## N) ...' or '### N) ...' heading."""
    raw, cur = [], None
    for line in text.splitlines():
        h = re.match(r"^#{2,3}\s+(.*)", line)
        if h:
            m = re.match(r"^\d+\)\s*(.*)", h.group(1).strip())
            cur = {"titulo": m.group(1).strip(), "linhas": []} if m else None
            if cur:
                raw.append(cur)
            continue
        if cur is not None:
            cur["linhas"].append(line)
    return [_parse_block(b) for b in raw]


def _parse_block(b):
    out = {"titulo": b["titulo"], "perfil": "", "tipo": "", "conexao": "", "textos": [],
           "bloqueado": bool(BLOCKED.search(b["titulo"]))}
    label, buf = None, None
    for line in b["linhas"] + [""]:
        s = line.strip()
        if s.startswith(">"):
            buf = (buf or []) + [s[1:].strip()]
            continue
        if buf is not None:
            texto = "\n".join(buf).strip()
            if texto and not re.match(r"(?i)^(atualizado em|obs\.?:|nota:)", texto):
                out["textos"].append({"rotulo": label, "texto": texto})
            buf, label = None, None
        if not s:
            continue
        m = re.match(r"^-\s*(?:Perfil|P[áa]gina)\s*:\s*(\S+)", s)
        if m and not out["perfil"]:
            out["perfil"] = m.group(1)
        if s.startswith("-"):
            mt = re.search(r"Tipo:\s*(.+)$", s)
            if mt:
                out["tipo"] = mt.group(1).strip()
            mc = re.match(r"^-\s*Conex[ãa]o:\s*(.+?)(?:\s*\|\s*Tipo:.*)?$", s)
            if mc:
                out["conexao"] = mc.group(1).strip()
        label = s.rstrip(":").strip() if s.endswith(":") else None
    return out


def find_block(blocks, profile_url, name):
    key = normalize_url(unquote(profile_url or ""))
    for b in blocks:
        if key and normalize_url(unquote(b["perfil"])) == key:
            return b
    folded = _fold(name)
    for b in blocks:
        if folded and re.sub(r"^\[[^\]]*\]\s*", "", _fold(b["titulo"])).startswith(folded):
            return b
    return None


def linkedin_type(tipo, conexao):
    """-> (kind, label). kind is 'convite' (invitation with a note) or 'mensagem' (direct message)."""
    t, c = _fold(tipo), _fold(conexao)
    if "conversa existente" in t + " " + c or "propria conversa" in t + " " + c:
        return "mensagem", "Mensagem direta (na conversa que já existe)"
    if "pagina" in t:
        return "mensagem", "Mensagem direta para a página"
    if "convite" in t and "mensagem direta" in t:
        return "mensagem", "Mensagem direta ou convite com nota"
    if "convite" in t:
        return "convite", "Convite com nota"
    if "mensagem" in t:
        return "mensagem", "Mensagem direta"
    if re.search(r"\bsim\b|1o grau", c):
        return "mensagem", "Mensagem direta"
    return "convite", "Convite com nota"


def split_recipient(cell):
    """'**ENVIADO 11/11** Ana Exemplo — Tech Recruiter, Loja' -> ('Ana Exemplo', 'Tech Recruiter, Loja')."""
    text = re.sub(r"\*\*[^*]*\*\*", "", cell).strip()
    text = re.sub(r"^\([^()]*\)\s*", "", text)
    parts = re.split(r"\s+[—–]\s+", text, maxsplit=1)
    return parts[0].strip(), (parts[1].strip() if len(parts) > 1 else "")


def priority_group(serve_para, confianca):
    """PROMPT section 6.0: 1 Vaga/Vaga + parceria 'Certeza'; 2 the other Vaga; 3 Freela/parceria; 4 Prospecção direta."""
    s, c = _fold(serve_para), _fold(confianca)
    if s.startswith("vaga"):
        return 1 if c.startswith("certeza") else 2
    if s.startswith("freela") or "white-label" in s:
        return 3
    if s.startswith("prospec"):
        return 4
    return 5


def _blocked_by_person(text, people):
    return any(mentions_person(text, p) for p in people)


def pending_linkedin(root, parcial, companies, blocked_nums, people):
    """Every LinkedIn message still to send, in the PROMPT 6.0 order. -> (items, hidden_by_nao_contatar)."""
    header, rows = table(section(parcial, "4."))
    c_num, c_who = _col(header, "#", default=1), _col(header, "destinat", "pessoa", default=2)
    c_con, c_url = _col(header, "conex", default=3), _col(header, "perfil", default=4)
    cache, items, hidden = {}, [], 0
    for idx, (cells, line) in enumerate(rows):
        if len(cells) < 3 or not is_pending_row(line):
            continue
        get = lambda i: cells[i] if i is not None and i < len(cells) else ""  # noqa: E731
        num = _number(get(c_num))
        url_m = URL.search(get(c_url)) or URL.search(line)
        url = url_m.group(0).rstrip(".") if url_m else ""
        if num in blocked_nums or _blocked_by_person(line, people):
            hidden += 1
            continue
        name, cargo = split_recipient(get(c_who))
        arq_m = re.search(r"rascunhos/linkedin/[^\s|]+?\.md", line)
        arq = arq_m.group(0) if arq_m else ""
        if arq and arq not in cache:
            path = root / arq
            cache[arq] = draft_blocks(path.read_text(encoding="utf-8")) if path.exists() else []
        block = find_block(cache.get(arq, []), url, name) or {}
        con_cell = get(c_con)
        tipo_tbl = con_cell.split("Tipo:", 1)[1] if "Tipo:" in con_cell else ""
        kind, kind_label = linkedin_type(block.get("tipo") or tipo_tbl, f"{block.get('conexao', '')} {con_cell}")
        textos = block.get("textos") or []
        info = companies.get(num, {})
        items.append({
            "id": "li:" + (normalize_url(unquote(url)) or f"{num}:{_fold(name)}"),
            "numero": num, "empresa": info.get("empresa") or "", "nome": name, "cargo": cargo,
            "perfil": url, "tipo": kind, "tipo_rotulo": kind_label,
            "texto": textos[0]["texto"] if textos else "",
            "texto_rotulo": textos[0]["rotulo"] if textos else None,
            "extras": textos[1:], "arquivo": arq,
            "grupo": priority_group(info.get("serve_para"), info.get("confianca")), "_linha": idx,
        })
    items.sort(key=lambda it: (it["grupo"], it["numero"] if it["numero"] is not None else 10**6, it["_linha"]))
    for i, it in enumerate(items, 1):
        it["ordem"] = i
        del it["_linha"]
    return items, hidden


def _email_file(path):
    """Read 'Para', 'Assunto' and the body of a rascunhos/email/*.md draft."""
    fields, body, in_body = {}, [], False
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^-\s*(Para|Assunto)\s*:\s*(.+)$", line.strip())
        if m and not in_body:
            fields[m.group(1).lower()] = m.group(2).strip()
            continue
        if not in_body and fields and not line.strip():
            in_body = True
            continue
        if in_body:
            body.append(line)
    fields["texto"] = "\n".join(body).strip()
    return fields


def pending_emails(root, parcial, companies, blocked_nums, people, file_mode):
    header, rows = table(section(parcial, "3."))
    c_to, c_subj = _col(header, "para", default=1), _col(header, "assunto", default=2)
    items = []
    for cells, line in rows:
        if len(cells) < 3 or not is_pending_row(line):
            continue
        num = _number(cells[0])
        to = cells[c_to] if c_to < len(cells) else ""
        extra = len(cells) - len(header)  # an unescaped '|' inside the subject splits it into more cells
        subject = " | ".join(cells[c_subj:c_subj + 1 + max(extra, 0)]) if c_subj < len(cells) else ""
        arq_m = re.search(r"rascunhos/email/[^\s|]+?\.md", line)
        arq = arq_m.group(0) if arq_m else ""
        fields = _email_file(root / arq) if arq and (root / arq).exists() else {}
        to = fields.get("para") or to
        if num in blocked_nums or _blocked_by_person(f"{line} {to}", people):
            continue
        item = {"id": f"em:{num}:{_fold(to)}", "numero": num, "empresa": companies.get(num, {}).get("empresa", ""),
                "para": to, "assunto": fields.get("assunto") or subject, "arquivo": arq}
        if file_mode:
            item["texto"] = fields.get("texto", "")
        items.append(item)
    return items


def merge_followups(parsed_rounds):
    """Follow-ups of every round; a later round replaces an earlier entry for the same companies (#N)."""
    merged = collections.OrderedDict()
    for r in parsed_rounds:
        for f in r["followups"]:
            nums = frozenset(int(n) for n in re.findall(r"#\s*(\d+)", f["quem"]))
            key = nums or frozenset([_fold(f["quem"])])
            for old in [k for k in merged if k <= key]:
                del merged[old]
            numeros = sorted(nums)
            fid = "fu:" + (",".join(str(n) for n in numeros) if numeros else f["quem"]) + ":" + f["data"]
            merged[key] = dict(f, rodada=r["data"], numeros=numeros, id=fid)
    return sorted(merged.values(), key=lambda f: f["data"])


def replies_needing_action(parsed_rounds):
    out, seen = [], set()
    for r in reversed(parsed_rounds):
        for text in r["responderam"]:
            if ACTION.search(text) and not HANDLED.search(text) and _fold(text) not in seen:
                seen.add(_fold(text))
                out.append({"id": "re:" + _fold(text)[:80], "texto": text, "rodada": r["data"]})
    return out


def numbered_items(body):
    return [re.sub(r"\*\*", "", m.group(1)).strip() for m in re.finditer(r"^\s*\d+\.\s+(.+)$", body, re.M)]


def _company_in(text, companies):
    m = re.search(r"#\s*(\d+)", text)
    if m:
        return int(m.group(1))
    folded, best = _fold(text), None
    for num, info in companies.items():
        for name in {_fold(info.get("empresa")), _fold(re.sub(r"\s*\(.*", "", info.get("empresa") or ""))}:
            if len(name) >= 4 and re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", folded):
                if best is None or len(name) > best[1]:
                    best = (num, len(name))
    return best[0] if best else None


def _company_report(root, num):
    folder = root / "relatorios"
    if num is None or not folder.exists():
        return None
    found = sorted(folder.glob(f"{num:03d}-*.md")) or sorted(folder.glob(f"{num}-*.md"))
    return found[0] if found else None


def job_link(root, num, clause):
    """The job URL of a decision: the one in the text, else the best match in the company's report."""
    m = URL.search(clause)
    if m:
        return m.group(0).rstrip(".:")
    report = _company_report(root, num)
    if not report:
        return None
    words = set(re.findall(r"[a-z0-9]{3,}", _fold(clause)))
    best, score = None, 0
    for u in URL.findall(report.read_text(encoding="utf-8")):
        u = u.rstrip(".:")
        if "linkedin.com/in/" in u:
            continue
        toks = set(re.findall(r"[a-z0-9]{3,}", _fold(unquote(u.split("://", 1)[-1]))))
        s = len(toks & words) + (0.5 if re.search(r"/jobs?/|/vagas?/|career|carreira|gupy", u) else 0)
        if s > score:
            best, score = u, s
    return best


def pending_decisions(root, parcial, parsed_rounds, companies, statuses):
    """Jobs the robot did not apply to and left for the candidate (management roles, language...)."""
    sources = [(f"rodada de {r['data'][8:10]}/{r['data'][5:7]}" if r.get("data") else r["arquivo"],
                [t["texto"] if isinstance(t, dict) else t for t in r["o_que_fazer"]]) for r in parsed_rounds]
    sources.append(("relatorio-parcial.md", numbered_items(section(parcial, "2."))))
    found = collections.OrderedDict()
    for origin, items in sources:
        for item in items:
            if item.startswith(SENT_MARK) or re.match(r"(?i)^feito\b", item):
                continue
            for clause in re.split(r"\s*(?=\bOpcional\s*:)", item):
                if not DECISION.search(clause):
                    continue
                num = _company_in(clause, companies)
                motivo = re.sub(r"^Opcional\s*:\s*", "", clause).strip()
                found[num if num is not None else _fold(motivo)[:60]] = {"numero": num, "motivo": motivo, "origem": origin}
    for num, st in statuses.items():
        if st == "VAGA_GESTAO_PARA_O_CANDIDATO_DECIDIR" and num not in found:
            found[num] = {"numero": num, "origem": "progresso.json",
                          "motivo": "Vaga de gestão: pela regra, o robô nunca se candidata sozinho. A decisão é sua."}
    out = []
    for key, d in found.items():
        num = d["numero"]
        if num is not None and statuses.get(num) in DECIDED:
            continue
        report = _company_report(root, num)
        out.append(dict(d, id=f"de:{key}", empresa=companies.get(num, {}).get("empresa", ""),
                        link=job_link(root, num, d["motivo"]),
                        relatorio=f"relatorios/{report.name}" if report else None))
    return out


DONE_LOG = Path("controle") / "painel-feitos.json"


def load_done(root):
    """Items the candidate marked as "Feito" in the panel (controle/painel-feitos.json)."""
    path = Path(root) / DONE_LOG
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("feitos", []) if path.exists() else []
    except ValueError:
        return []


def build_pending(root, prog, parsed_rounds, companies, statuses, today):
    parcial_path = root / "relatorio-parcial.md"
    parcial = parcial_path.read_text(encoding="utf-8") if parcial_path.exists() else ""
    blocked_nums, people = do_not_contact(prog)
    file_mode = read_profile_fields(root / "perfil.local.md").get("modo_email", "arquivo") != "gmail_rascunho"
    linkedin, hidden = pending_linkedin(root, parcial, companies, blocked_nums, people)
    emails = pending_emails(root, parcial, companies, blocked_nums, people, file_mode)
    decisions = pending_decisions(root, parcial, parsed_rounds, companies, statuses)
    replies = replies_needing_action(parsed_rounds)
    followups = [f for f in merge_followups(parsed_rounds)
                 if not set(f["numeros"]) & blocked_nums and not _blocked_by_person(f["quem"], people)]
    replies = [r for r in replies if _company_in(r["texto"], companies) not in blocked_nums
               and not _blocked_by_person(r["texto"], people)]
    # the candidate's click is the source of truth: an item marked "Feito" never comes back as pending
    done = load_done(root)
    ids = {f["id"] for f in done}
    linkedin = [it for it in linkedin if it["id"] not in ids]
    for i, it in enumerate(linkedin, 1):
        it["ordem"] = i
    emails = [it for it in emails if it["id"] not in ids]
    decisions = [it for it in decisions if it["id"] not in ids]
    replies = [it for it in replies if it["id"] not in ids]
    followups = [f for f in followups if f["id"] not in ids]
    due = [f for f in followups if f["data"] <= today]
    # names on only one side: section 4 of relatorio-parcial.md (no ✅, no NÃO ENVIAR) vs this list
    listed = {_fold(it["nome"]) for it in linkedin}
    report_names = section4_pending_names(parcial)
    done_names = {_fold(f.get("descricao", "")[len("LinkedIn para "):]) for f in done if f.get("tipo") == "linkedin"}
    only_report = [n for n in report_names if _fold(n) not in listed]
    differences = [{"nome": n, "lado": "relatorio", "motivo": "marcado como Feito no painel"}
                   for n in only_report if _fold(n) in done_names]
    blocked = [n for n in only_report if _fold(n) not in done_names]
    if blocked:  # NAO_CONTATAR people are never named in the panel, not even here
        differences.append({"nome": f"{len(blocked)} {'pessoa' if len(blocked) == 1 else 'pessoas'} NAO_CONTATAR",
                            "lado": "relatorio", "motivo": "marque NÃO ENVIAR no relatório"})
    report_folded = {_fold(n) for n in report_names}
    differences += [{"nome": it["nome"], "lado": "lista", "motivo": ""} for it in linkedin if _fold(it["nome"]) not in report_folded]
    return {
        "conferencia_diferencas": differences,
        "enviados_hoje": [{k: f.get(k) for k in ("id", "tipo", "data", "descricao", "empresa", "numero")}
                          for f in done if f.get("data") == today],
        "hoje": today,
        "totais": {"linkedin": len(linkedin), "email": len(emails), "followups_vencidos": len(due),
                   "decisoes": len(decisions), "respostas": len(replies)},
        "conferencia": {"linkedin_secao4": count_linkedin_section4(parcial), "linkedin_painel": len(linkedin),
                        "ocultos_nao_contatar": hidden, "fonte": "relatorio-parcial.md" if parcial else None},
        "modo_email": "arquivo" if file_mode else "gmail_rascunho",
        "gmail_rascunhos": GMAIL_DRAFTS,
        "linkedin": linkedin, "emails": emails, "decisoes": decisions, "respostas": replies,
    }, followups


def _sheet_rows(root):
    path = root / "relatorio-final.xlsx"
    if not path.exists():
        path = find_company_sheet(root)
    if not path or not Path(path).exists():
        return [], []
    wb = openpyxl.load_workbook(path, read_only=True)
    try:
        rows = list(wb["Empresas"].iter_rows(values_only=True))
    finally:
        wb.close()  # read-only mode keeps the file open; Windows could not replace it afterwards
    return (list(rows[0]), rows[1:]) if rows else ([], [])


def sheet_companies(root):
    """{numero: {empresa, serve_para, confianca}} from the company sheet."""
    header, rows = _sheet_rows(root)
    idx = {name: header.index(name) for name in ("Empresa", "Serve para", "Confiança") if name in header}
    out = {}
    for r in rows:
        try:
            num = int(r[0])
        except (TypeError, ValueError, IndexError):
            continue
        get = lambda k: (r[idx[k]] if k in idx and idx[k] < len(r) else None) or ""  # noqa: E731
        out[num] = {"empresa": str(get("Empresa")), "serve_para": str(get("Serve para")), "confianca": str(get("Confiança"))}
    return out


def company_types(root, statuses):
    header, rows = _sheet_rows(root)
    if not header:
        return [], 0
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


def build(root, today=None):
    today = today or date.today().isoformat()
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
    parsed_rounds = [parse_round(r) for r in rounds]
    latest = parsed_rounds[-1] if parsed_rounds else None
    replied = []
    for parsed in parsed_rounds[-3:]:
        replied += [{"texto": t, "rodada": parsed["data"]} for t in parsed["responderam"]]

    companies = sheet_companies(root)
    for e in prog.get("empresas", []):
        companies.setdefault(int(e["numero"]), {}).setdefault("empresa", e.get("empresa") or "")
        if not companies[int(e["numero"])].get("empresa"):
            companies[int(e["numero"])]["empresa"] = e.get("empresa") or ""
    pending, followups = build_pending(root, prog, parsed_rounds, companies, statuses, today)

    return {
        "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "demo": False,
        "pendentes": pending,
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


def open_panel(target):
    """Open the panel (a URL or a file) in the default browser (macOS, Linux and Windows). True if it opened."""
    uri = target if str(target).startswith("http") else Path(target).resolve().as_uri()
    try:
        return bool(webbrowser.open(uri))
    except webbrowser.Error:
        return False


def _running_server(root):
    """URL of a server already running for this project, or None."""
    state = Path(root) / "controle" / ".painel-servidor.json"
    try:
        info = json.loads(state.read_text(encoding="utf-8"))
        with urllib.request.urlopen(f"http://127.0.0.1:{int(info['porta'])}/api/estado", timeout=1.5) as r:
            if Path(json.loads(r.read().decode("utf-8")).get("raiz") or "").resolve() == Path(root).resolve():
                return info["url"]
    except (OSError, ValueError, KeyError):
        pass
    return None


def ensure_server(root, wait=45.0):
    """Start scripts/servidor_painel.py in the background (detached, all 3 systems) unless one is running."""
    url = _running_server(root)
    if url:
        return url
    script = Path(__file__).resolve().parent / "servidor_painel.py"
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    else:
        kwargs["start_new_session"] = True
    log = Path(root) / "controle" / ".painel-servidor.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "ab") as fh:
        subprocess.Popen([sys.executable, str(script), "--raiz", str(root)], stdin=subprocess.DEVNULL,
                         stdout=fh, stderr=fh, close_fds=True, cwd=str(root), **kwargs)
    deadline = time.time() + wait
    while time.time() < deadline:
        url = _running_server(root)
        if url:
            return url
        time.sleep(0.3)
    return None


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
    url = None if "--arquivo" in args else ensure_server(root)
    if url is None and "--arquivo" not in args:
        print("Não consegui iniciar o servidor local; abrindo o arquivo (o Feito fica desativado).")
    target = url or index_html
    if (url or index_html.exists()) and open_panel(target):
        print(f"Painel aberto no navegador: {target if url else 'painel/index.html'}")
    else:
        print(f"Abra no navegador: {url or index_html.resolve().as_uri()}")


if __name__ == "__main__":
    main()
