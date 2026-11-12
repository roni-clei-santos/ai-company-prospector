#!/usr/bin/env python3
"""Generate a job-tailored CV (PDF) from the candidate's fixed facts.

Usage: python3 scripts/gerar_cv.py <config.json> <output.pdf> [--base controle/cv-base.json]

- The base file (default: controle/cv-base.json, personal and gitignored) holds the FIXED facts:
  name, contact line, experiences (role, dates, bullets), education, languages, default skills.
  See examples/cv-base.example.json for the format.
- The per-job config can change: titulo, resumo, competencias order/emphasis, bullets_extras per
  experience key (facts only) and an optional "destaques" block.
Experiences, roles and dates come from the base file and cannot be removed by the config.
"""
import argparse
import json
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASE = ROOT / "controle" / "cv-base.json"

INK = HexColor("#1a1a1a")
MUTED = HexColor("#555555")


def styles():
    base = dict(fontName="Helvetica", textColor=INK, alignment=TA_LEFT)
    return {
        "nome": ParagraphStyle("nome", fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=INK),
        "titulo": ParagraphStyle("titulo", fontName="Helvetica-Bold", fontSize=10.5, leading=14, textColor=INK),
        "contato": ParagraphStyle("contato", fontSize=8.5, leading=11, textColor=MUTED, fontName="Helvetica"),
        "secao": ParagraphStyle("secao", fontName="Helvetica-Bold", fontSize=10, leading=13, spaceBefore=7, spaceAfter=2, textColor=INK),
        "texto": ParagraphStyle("texto", fontSize=8.8, leading=12, **base),
        "cargo": ParagraphStyle("cargo", fontName="Helvetica-Bold", fontSize=9, leading=12, spaceBefore=4, textColor=INK),
        "data": ParagraphStyle("data", fontSize=8, leading=10, textColor=MUTED, fontName="Helvetica"),
        "bullet": ParagraphStyle("bullet", fontSize=8.6, leading=11.2, **base),
    }


def bullets(items, st):
    return ListFlowable(
        [ListItem(Paragraph(i, st["bullet"]), leftIndent=8, value="•") for i in items],
        bulletType="bullet", start="•", leftIndent=8, bulletFontSize=7,
    )


def load_base(path):
    path = Path(path)
    if not path.exists():
        raise SystemExit(f"Base file not found: {path} (copy examples/cv-base.example.json and fill it in)")
    return json.loads(path.read_text(encoding="utf-8"))


def generate(cfg, output, base):
    st = styles()
    name = base["nome"]
    doc = SimpleDocTemplate(output, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm,
                            topMargin=14 * mm, bottomMargin=14 * mm,
                            title=f"{name} — Currículo", author=name)
    el = [
        Paragraph(name, st["nome"]),
        Paragraph(cfg.get("titulo", base.get("titulo_padrao", "")), st["titulo"]),
        Paragraph(base.get("contato", ""), st["contato"]),
        Spacer(1, 3),
        HRFlowable(width="100%", thickness=0.6, color=HexColor("#bbbbbb")),
        Paragraph("RESUMO", st["secao"]),
        Paragraph(cfg["resumo"], st["texto"]),
    ]
    if cfg.get("destaques"):
        el += [Paragraph(cfg.get("titulo_destaques", "DESTAQUES PARA A VAGA"), st["secao"]), bullets(cfg["destaques"], st)]
    if base.get("formacao"):
        el += [Paragraph("CERTIFICAÇÃO E FORMAÇÃO", st["secao"]), bullets(base["formacao"], st)]
    comps = cfg.get("competencias", base.get("competencias_padrao", []))
    if comps:
        el += [Paragraph("COMPETÊNCIAS", st["secao"]), bullets([f"<b>{k}:</b> {v}" for k, v in comps], st)]
    el.append(Paragraph("EXPERIÊNCIA", st["secao"]))
    extras = cfg.get("bullets_extras", {})
    for exp in base["experiencias"]:
        el.append(Paragraph(exp["cargo"], st["cargo"]))
        el.append(Paragraph(exp["datas"], st["data"]))
        items = list(exp.get("itens", [])) + extras.get(exp["chave"], [])
        if items:
            el.append(bullets(items, st))
    if base.get("antes"):
        el.append(Spacer(1, 3))
        el.append(Paragraph(base["antes"], st["data"]))
    if base.get("idiomas"):
        el += [Paragraph("IDIOMAS", st["secao"]), Paragraph(base["idiomas"], st["texto"])]
    doc.build(el)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("config")
    ap.add_argument("output")
    ap.add_argument("--base", default=str(DEFAULT_BASE))
    args = ap.parse_args()
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    generate(cfg, args.output, load_base(args.base))
    print("ok", args.output)


if __name__ == "__main__":
    main()
