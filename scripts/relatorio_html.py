#!/usr/bin/env python3
"""Pre-render the Markdown reports cited by the panel (relatorios/*.md) as pages in painel/relatorios/.

Standard library only. Supports headings, lists (nested), bold, italic, inline code, links (only
http/https, opened with rel="noopener"), bare http(s) URLs, tables, blockquotes, rules and code
blocks. ALL content is HTML-escaped first; the page has no scripts (Content-Security-Policy).
The pages open the same way from file:// and from the local server (http://127.0.0.1).

Usage: python3 scripts/relatorio_html.py <arquivo.md> [<saida.html>]
"""
import html
import re
import sys
from pathlib import Path

SAFE_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*\.html$")
OUT_DIR = Path("painel") / "relatorios"

_LINK = re.compile(r"\[([^\]\n]+)\]\(((?:[^()\s]|\([^()\s]*\))+)\)")
_URL = re.compile(r"https?://[^\s<>\"'`]+", re.I)
_BOLD = re.compile(r"\*\*(?!\s)(.+?)(?<!\s)\*\*")
_ITALIC_STAR = re.compile(r"(?<![*\w])\*(?![\s*])(.+?)(?<![\s*])\*(?![*\w])")
_ITALIC_UNDER = re.compile(r"(?<![\w])_(?![\s_])(.+?)(?<![\s_])_(?![\w])")
_LIST = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")
_TABLE_SEP = re.compile(r"^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?$")


def html_name(md_name):
    """relatorios/001-Loja Exemplo.md -> '001-loja-exemplo.html' (always matches SAFE_NAME)."""
    stem = re.sub(r"[^a-z0-9-]+", "-", Path(str(md_name)).stem.lower()).strip("-")
    return (stem or "relatorio") + ".html"


def _fmt(escaped):
    escaped = _BOLD.sub(r"<strong>\1</strong>", escaped)
    escaped = _ITALIC_STAR.sub(r"<em>\1</em>", escaped)
    return _ITALIC_UNDER.sub(r"<em>\1</em>", escaped)


def _anchor(url, label_html):
    return f'<a href="{html.escape(url, quote=True)}" target="_blank" rel="noopener">{label_html}</a>'


def inline(text):
    """One line of Markdown -> safe HTML."""
    keep = []

    def stash(fragment):
        keep.append(fragment)
        return f"\x00{len(keep) - 1}\x00"

    def link(m):
        label, url = m.group(1), m.group(2)
        if re.match(r"^https?://", url, re.I):
            return stash(_anchor(url, _fmt(html.escape(label, quote=False))))
        return stash(_fmt(html.escape(label, quote=False)))  # other schemes (javascript:, file:...) -> plain text

    def bare(m):
        url = m.group(0)
        tail = ""
        while url and url[-1] in ".,;:!?)]":
            tail = url[-1] + tail
            url = url[:-1]
        return stash(_anchor(url, html.escape(url, quote=False))) + tail

    out = []
    for part in re.split(r"(`[^`\n]+`)", text.replace("\x00", "")):
        if len(part) > 1 and part.startswith("`") and part.endswith("`"):
            out.append(stash("<code>" + html.escape(part[1:-1], quote=False) + "</code>"))
            continue
        part = _LINK.sub(link, part)
        part = _URL.sub(bare, part)
        out.append(_fmt(html.escape(part, quote=False)))
    s = "".join(out)
    while "\x00" in s:
        s = re.sub(r"\x00(\d+)\x00", lambda m: keep[int(m.group(1))], s)
    return s


def _cells(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def _list_html(block):
    items = []
    for line in block:
        m = _LIST.match(line)
        if m:
            items.append([len(m.group(1).replace("\t", "    ")), m.group(2)[0].isdigit(), m.group(3)])
        elif items:
            items[-1][2] += " " + line.strip()
    parts, stack = [], []
    for indent, ordered, text in items:
        tag = "ol" if ordered else "ul"
        while stack and (indent < stack[-1][0] or (indent == stack[-1][0] and tag != stack[-1][1])):
            parts.append(f"</li></{stack.pop()[1]}>")
        if not stack or indent > stack[-1][0]:
            parts.append(f"<{tag}>")
            stack.append((indent, tag))
        else:
            parts.append("</li>")
        parts.append(f"<li>{inline(text)}")
    while stack:
        parts.append(f"</li></{stack.pop()[1]}>")
    return "".join(parts)


def convert(md):
    """Markdown text -> HTML body (every piece of content escaped)."""
    lines = md.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out, para, i = [], [], 0

    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para.clear()

    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if s.startswith("```"):
            flush()
            i += 1
            code = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1
            out.append("<pre><code>" + html.escape("\n".join(code), quote=False) + "</code></pre>")
            continue
        if not s:
            flush()
            i += 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*?)\s*#*$", s)
        if m:
            flush()
            n = len(m.group(1))
            out.append(f"<h{n}>{inline(m.group(2))}</h{n}>")
            i += 1
            continue
        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", s):
            flush()
            out.append("<hr>")
            i += 1
            continue
        if s.startswith("|") and i + 1 < len(lines) and _TABLE_SEP.match(lines[i + 1].strip()):
            flush()
            head = _cells(s)
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(_cells(lines[i]))
                i += 1
            th = "".join(f"<th>{inline(c)}</th>" for c in head)
            body = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows)
            out.append(f'<div class="scroll-x"><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>')
            continue
        if s.startswith(">"):
            flush()
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip()[1:].lstrip())
                i += 1
            out.append("<blockquote>" + convert("\n".join(quote)) + "</blockquote>")
            continue
        if _LIST.match(line):
            flush()
            block = []
            while i < len(lines) and (_LIST.match(lines[i]) or (lines[i][:1] in (" ", "\t") and lines[i].strip())):
                block.append(lines[i])
                i += 1
            out.append(_list_html(block))
            continue
        para.append(s)
        i += 1
    flush()
    return "\n".join(out)


CSS = """
  :root { --bg: #0B1F3A; --card: #12294A; --line: #26446F; --ink: #F4F7FB; --ink-2: #B9C6D8; --ink-3: #8597B0; --accent: #FF7A1A; --code: #1B375F; }
  @media (prefers-color-scheme: light) {
    :root { --bg: #F6F8FB; --card: #FFFFFF; --line: #D8E0EB; --ink: #0B1F3A; --ink-2: #33496A; --ink-3: #5B7090; --accent: #C2540A; --code: #EEF2F7; }
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--ink); font-family: Inter, system-ui, -apple-system, "Segoe UI", sans-serif; font-size: 15px; line-height: 1.6; }
  .wrap { max-width: 920px; margin: 0 auto; padding: 22px 16px 60px; }
  .back { margin-bottom: 18px; }
  .back a { display: inline-flex; gap: 6px; padding: 7px 12px; border-radius: 9px; border: 1px solid var(--line); background: var(--card); color: var(--ink); font-weight: 600; font-size: 13px; text-decoration: none; }
  .back a:hover { border-color: var(--accent); }
  article { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 22px; overflow-wrap: anywhere; }
  h1 { font-size: 26px; line-height: 1.2; margin: 0 0 14px; }
  h2 { font-size: 19px; margin: 26px 0 10px; }
  h3, h4, h5, h6 { font-size: 15px; margin: 20px 0 8px; color: var(--ink-2); }
  a { color: var(--accent); }
  code { background: var(--code); padding: 1px 5px; border-radius: 5px; font-size: 13px; }
  pre { background: var(--code); padding: 12px; border-radius: 10px; overflow-x: auto; }
  pre code { padding: 0; background: none; }
  blockquote { margin: 12px 0; padding: 4px 14px; border-left: 3px solid var(--accent); color: var(--ink-2); }
  hr { border: 0; border-top: 1px solid var(--line); margin: 22px 0; }
  ul, ol { padding-left: 22px; }
  li { margin: 3px 0; }
  .scroll-x { overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 14px; margin: 10px 0; }
  th, td { text-align: left; padding: 7px 8px; border-bottom: 1px solid var(--line); vertical-align: top; }
  th { color: var(--ink-3); font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }
"""


def page(md, fallback_title):
    body = convert(md)
    m = re.search(r"<h1>(.*?)</h1>", body)
    title = re.sub(r"<[^>]+>", "", m.group(1)) if m else html.escape(fallback_title)
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src https: data:">
<meta name="referrer" content="no-referrer">
<title>{title} · Painel da prospecção</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<nav class="back"><a href="../index.html">← Voltar ao painel</a></nav>
<article class="md">
{body}
</article>
</div>
</body>
</html>
"""


def render_reports(root, rel_paths):
    """Render each cited relatorios/*.md into painel/relatorios/<name>.html. Returns {md path: html path}."""
    root = Path(root)
    out_dir = root / OUT_DIR
    done = {}
    for rel in sorted({p for p in rel_paths if p}):
        src = root / rel
        if not src.is_file() or src.suffix.lower() != ".md":
            continue
        name = html_name(src.name)
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / name
        text = page(src.read_text(encoding="utf-8", errors="replace"), src.stem)
        if not target.exists() or target.read_text(encoding="utf-8", errors="replace") != text:
            target.write_text(text, encoding="utf-8")
        done[rel] = f"relatorios/{name}"
    return done


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_suffix(".html")
    dst.write_text(page(src.read_text(encoding="utf-8"), src.stem), encoding="utf-8")
    print(dst)
