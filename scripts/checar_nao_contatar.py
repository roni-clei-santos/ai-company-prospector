#!/usr/bin/env python3
"""Check that no pending draft goes to a person or company marked NAO_CONTATAR.

Reads controle/progresso.json:
  - companies whose status is NAO_CONTATAR (by number: drafts are named <numero>-<empresa>*.md)
  - people in progresso.json > nao_contatar (matched by e-mail, LinkedIn URL or full name)

Scans rascunhos/email/*.md (one draft per file) and rascunhos/linkedin/*.md (one block per
"##"/"###" heading, the intro before the first heading is skipped). A draft is
pending unless it says "ENVIADO DD/MM/AAAA" or "NÃO ENVIAR". Every pending block that targets a
NAO_CONTATAR person or company is reported; mark it "NÃO ENVIAR" (or delete the draft).

Usage: python3 scripts/checar_nao_contatar.py [project folder]     (default: current project)
Exit code 0 = OK, 1 = problems found.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DO_NOT_CONTACT, do_not_contact, mentions_person, project_root  # noqa: E402

HEADING = re.compile(r"^#{2,3}\s")
SENT = re.compile(r"\bENVIADO\s+\d{2}/\d{2}/\d{4}", re.I)
BLOCKED = re.compile(r"N[ÃA]O\s+ENVIAR", re.I)
NUMBER = re.compile(r"^0*(\d+)-")


def blocks(text):
    """Split a draft into (first_line_number, block_text) by level-2/3 headings."""
    lines = text.split("\n")
    out, start = [], 0
    for i, line in enumerate(lines):
        if HEADING.match(line) and i > start:
            out.append((start + 1, "\n".join(lines[start:i])))
            start = i
    out.append((start + 1, "\n".join(lines[start:])))
    return out


def is_pending(block):
    return not SENT.search(block) and not BLOCKED.search(block)


def check(root):
    progress_path = root / "controle" / "progresso.json"
    if not progress_path.exists():
        return []
    numbers, people = do_not_contact(json.loads(progress_path.read_text(encoding="utf-8")))
    if not numbers and not people:
        return []
    problems = []
    for folder in ("linkedin", "email"):
        for f in sorted((root / "rascunhos" / folder).glob("*.md")):
            m = NUMBER.match(f.name)
            company_blocked = bool(m) and int(m.group(1)) in numbers
            rel = f.relative_to(root).as_posix()
            text = f.read_text(encoding="utf-8")
            # An e-mail file is one draft. A LinkedIn file has one block per person after an intro.
            parts = [(1, text)] if folder == "email" else blocks(text)
            for line_no, block in (parts if len(parts) == 1 else parts[1:]):
                if not is_pending(block):
                    continue
                if company_blocked:
                    problems.append(f"{DO_NOT_CONTACT} empresa #{int(m.group(1))}: {rel} {line_no}")
                for p in people:
                    if mentions_person(block, p):
                        who = p.get("nome") or p.get("email") or p.get("linkedin_url")
                        problems.append(f"{DO_NOT_CONTACT} pessoa {who}: {rel} {line_no}")
    return problems


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]).resolve() if argv else project_root()
    problems = check(root)
    for p in problems:
        print(p)
    print("OK" if not problems else "PROBLEMAS")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
