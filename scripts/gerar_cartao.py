#!/usr/bin/env python3
"""Build the README stats card (assets/stats-*.svg) from YOUR project: counts only, never names.

Reads (all personal, gitignored): controle/progresso.json, rascunhos/linkedin/*.md, rascunhos/email/*.md
and relatorios/rodada-*.md. Writes four SVGs (dark/light x Portuguese/English) with four numbers:
companies processed, drafts created, replies received and rounds.

Usage (from the project folder; on Windows use `py -3`):
  python3 scripts/gerar_cartao.py               write assets/stats-dark.svg, stats-light.svg (+ .en.svg)
  python3 scripts/gerar_cartao.py --print       only print the numbers
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import project_root  # noqa: E402
from gerar_painel import parse_round  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
RECIPIENT = re.compile(r"^\s*-\s*(\*\*)?(Perfil|Página|LinkedIn)(\*\*)?:", re.M)

LABELS = {
    "pt": ["empresas processadas", "rascunhos criados", "respostas recebidas", "rodadas"],
    "en": ["companies processed", "drafts created", "replies received", "rounds"],
}
THEMES = {
    "dark": {"bg": "#0B1F3A", "card": "#12294A", "line": "#26446F", "num": "#FF7A1A", "label": "#B9C6D8"},
    "light": {"bg": "#FFFFFF", "card": "#F4F7FB", "line": "#D5DEEA", "num": "#E8650A", "label": "#3A4A63"},
}


def collect(root):
    """Return the four counts (ints). Missing files count as zero."""
    prog_path = root / "controle" / "progresso.json"
    prog = json.loads(prog_path.read_text(encoding="utf-8")) if prog_path.exists() else {}
    companies = len(prog.get("empresas", []))
    li = root / "rascunhos" / "linkedin"
    em = root / "rascunhos" / "email"
    drafts = sum(len(RECIPIENT.findall(p.read_text(encoding="utf-8"))) for p in li.glob("*.md")) if li.exists() else 0
    drafts += len(list(em.glob("*.md"))) if em.exists() else 0
    rounds_files = sorted((root / "relatorios").glob("rodada-*.md")) if (root / "relatorios").exists() else []
    replies = sum(len(parse_round(p)["responderam"]) for p in rounds_files)
    sessions = [int(h["sessao"]) for h in prog.get("historico", []) if str(h.get("sessao", "")).isdigit()]
    rounds = max([len(rounds_files)] + sessions)
    return [companies, drafts, replies, rounds]


def svg(numbers, lang, theme):
    t = THEMES[theme]
    w, h, pad, gap = 1200, 190, 24, 16
    cw = (w - 2 * pad - 3 * gap) / 4
    cells = []
    for i, (n, label) in enumerate(zip(numbers, LABELS[lang])):
        x = pad + i * (cw + gap)
        cells.append(f'''  <g class="c" style="animation-delay:{0.12 * i:.2f}s">
    <rect x="{x:.1f}" y="{pad}" width="{cw:.1f}" height="{h - 2 * pad}" rx="16" fill="{t['card']}" stroke="{t['line']}"/>
    <text x="{x + cw / 2:.1f}" y="{pad + 78}" class="n">{f"{n:,}".replace(",", "." if lang == "pt" else ",")}</text>
    <text x="{x + cw / 2:.1f}" y="{pad + 116}" class="l">{label}</text>
  </g>''')
    title = "Números do uso real do autor" if lang == "pt" else "Numbers from the author's real use"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-labelledby="t">
  <title id="t">{title}: {", ".join(f"{n} {l}" for n, l in zip(numbers, LABELS[lang]))}</title>
  <style>
    .n {{ font: 800 52px Inter, -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; fill: {t['num']}; text-anchor: middle; letter-spacing: -1px; font-variant-numeric: tabular-nums; }}
    .l {{ font: 600 17px Inter, -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; fill: {t['label']}; text-anchor: middle; }}
    .c {{ animation: in .7s ease-out backwards; }}
    @keyframes in {{ from {{ opacity: 0; transform: translateY(8px); }} to {{ opacity: 1; transform: none; }} }}
    @media (prefers-reduced-motion: reduce) {{ .c {{ animation: none; }} }}
  </style>
  <rect width="{w}" height="{h}" rx="20" fill="{t['bg']}"/>
{chr(10).join(cells)}
</svg>
'''


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    numbers = collect(project_root())
    print("empresas={} rascunhos={} respostas={} rodadas={}".format(*numbers))
    if "--print" in args:
        return
    out = REPO / "assets"
    out.mkdir(exist_ok=True)
    for theme in THEMES:
        (out / f"stats-{theme}.svg").write_text(svg(numbers, "pt", theme), encoding="utf-8")
        (out / f"stats-{theme}.en.svg").write_text(svg(numbers, "en", theme), encoding="utf-8")
    print("assets/stats-dark.svg, stats-light.svg, stats-dark.en.svg, stats-light.en.svg")


if __name__ == "__main__":
    main()
