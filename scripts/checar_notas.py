#!/usr/bin/env python3
"""Check LinkedIn invite notes in rascunhos/linkedin/*.md.

Every "nota de convite" must have a text of at most 200 characters, without long dashes (—)
and without the phrases listed in perfil.local.md > palavras_proibidas.

The invite note is recognized in any of these formats (case-insensitive marker):
  - "- Tipo: nota de convite (181 caracteres)" followed by a "> text" line
  - a heading "### Nota de convite" (any case) followed by a quote, a code block or a paragraph
  - a label line "Nota de convite:" followed by the text
  - inline: "**Nota de convite:** text" / "Nota de convite: text"

Usage: python3 scripts/checar_notas.py [folder]     (default: rascunhos/linkedin)
Exit code 0 = OK, 1 = problems found.
"""
import ast
import glob
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import project_root  # noqa: E402

MAX_CHARS = 200
MARKER = re.compile(r"nota\s+de\s+convite", re.I)
# Text after the marker on the same line, e.g. "Nota de convite: Oi, ..." or "**Nota de convite:** Oi"
INLINE = re.compile(r"nota\s+de\s+convite\s*(?:\([^)]*\))?\s*\**\s*:\s*\**\s*(?P<text>\S.*)$", re.I)
METADATA = re.compile(r"^\s*[-*+]\s+\**[^:]{1,60}\**\s*:")
LOOKAHEAD = 8


def _is_label(line):
    """A line that only introduces something (heading or 'Something:'), not note content."""
    s = line.strip()
    return s.startswith("#") or (s.endswith(":") and len(s) <= 80) or bool(METADATA.match(s))


def _block_at(lines, j):
    """Return (note_text, end_index) for the content block starting at line j, or (None, j)."""
    s = lines[j].strip()
    if s.startswith("```") or s.startswith("~~~"):
        fence = s[:3]
        body = []
        k = j + 1
        while k < len(lines) and not lines[k].strip().startswith(fence):
            body.append(lines[k])
            k += 1
        return "\n".join(body).strip(), k
    if s.startswith(">"):
        body = []
        k = j
        while k < len(lines) and lines[k].strip().startswith(">"):
            body.append(re.sub(r"^\s*>\s?", "", lines[k]))
            k += 1
        return "\n".join(body).strip(), k - 1
    body = []
    k = j
    while k < len(lines) and lines[k].strip() and not _is_label(lines[k]):
        body.append(lines[k].strip())
        k += 1
    return (" ".join(body).strip() or None), k - 1


def extract_notes(text):
    """Return a list of (line_number, note_text_or_None) for every invite note marker."""
    lines = text.split("\n")
    results = []
    used_starts = set()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not MARKER.search(line) or line.strip().startswith(">"):
            i += 1
            continue
        m = INLINE.search(line)
        if m and len(m.group("text").strip("* ")) >= 15:
            results.append((i + 1, m.group("text").strip().strip("*").strip()))
            i += 1
            continue
        note, start = None, None
        j = i + 1
        seen = 0
        while j < len(lines) and seen < LOOKAHEAD:
            s = lines[j].strip()
            if not s:
                j += 1
                continue
            seen += 1
            if s.startswith("#") and not MARKER.search(s):
                break  # next section: this marker has no note
            if _is_label(lines[j]) and not s.startswith((">", "```", "~~~")):
                j += 1
                continue
            note, end = _block_at(lines, j)
            start = j
            break
        if start is not None and start in used_starts:
            i += 1  # same note already counted by a previous marker
            continue
        if start is not None:
            used_starts.add(start)
        results.append((i + 1, note))
        i += 1
    return results


def forbidden_phrases():
    path = project_root() / "perfil.local.md"
    if not path.exists():
        return []
    m = re.search(r"^palavras_proibidas:\s*(\[.*\])", path.read_text(encoding="utf-8"), re.M)
    if not m:
        return []
    try:
        return [str(x) for x in ast.literal_eval(m.group(1))]
    except (ValueError, SyntaxError):
        return []


def check_file(path, banned):
    problems = []
    text = Path(path).read_text(encoding="utf-8")
    for line_no, note in extract_notes(text):
        if note is None:
            problems.append(f"SEM NOTA {path} {line_no}")
        elif len(note) > MAX_CHARS:
            problems.append(f"LONGA {len(note)} {path} {line_no}")
    quoted = [m.group(0) for m in re.finditer(r"^> .*$", text, re.M)]
    notes = [n for _, n in extract_notes(text) if n]
    for chunk in quoted + notes:
        low = chunk.lower()
        if "—" in chunk or any(b.lower() in low for b in banned):
            problems.append(f"ESTILO {path} {chunk[:60]}")
    return sorted(set(problems), key=problems.index)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    folder = Path(argv[0]) if argv else project_root() / "rascunhos" / "linkedin"
    banned = forbidden_phrases()
    problems = []
    for f in sorted(glob.glob(str(folder / "*.md"))):
        problems += check_file(f, banned)
    for p in problems:
        print(p)
    print("OK" if not problems else "PROBLEMAS")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
