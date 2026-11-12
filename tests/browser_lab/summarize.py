#!/usr/bin/env python3
"""Join the results.json of every browser-lab-<so> artifact into one Markdown table.

Usage: python tests/browser_lab/summarize.py <artifacts folder> <resumo.md>
"""
import json
import sys
from pathlib import Path

ESPERADO = {"macos": ["safari", "chrome", "edge", "firefox", "brave"],
            "windows": ["chrome", "edge", "firefox", "brave"],
            "ubuntu": ["chrome", "firefox"]}
NOMES = {"safari": "Safari", "chrome": "Chrome", "edge": "Edge", "firefox": "Firefox", "brave": "Brave"}
SOS = {"macos": "macOS", "windows": "Windows", "ubuntu": "Ubuntu"}
COLUNAS = [("A", "A arquivo+servidor"), ("B", "B arquivo sem servidor (fila)"), ("C", "C http"), ("D", "D auditoria")]


def short(text, words=8):
    w = str(text or "").replace("|", "/").replace("\n", " ").split()
    return " ".join(w[:words]) + (" …" if len(w) > words else "")


def cell(c):
    if not c:
        return "AMBIENTE (sem medida)"
    if c["status"] == "ok":
        return "✅"
    if c["status"] == "ambiente":
        return f"AMBIENTE ({short(c.get('motivo'), 10)})"
    return f"❌ ({short(c.get('motivo'))})"


def main(folder, out):
    found = {}
    for path in sorted(Path(folder).rglob("results.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for r in data.get("navegadores", []):
            found[(data["so"], r["navegador"])] = r
    head = ["SO", "Navegador", "Versão"] + [c[1] for c in COLUNAS]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    detalhes, avisos, falhas = [], [], 0
    for so, navs in ESPERADO.items():
        for nav in navs:
            r = found.get((so, nav))
            if r is None:
                cells, versao = ["AMBIENTE (job sem resultados)"] * len(COLUNAS), "?"
                avisos.append(f"{SOS[so]} / {NOMES[nav]}: job sem resultados")
            elif r.get("erro_do_laboratorio"):
                cells, versao = ["❌ (erro do laboratório)"] * len(COLUNAS), "?"
                falhas += 1
                detalhes.append(f"- **{SOS[so]} / {NOMES[nav]}**: erro do laboratório\n```\n{r['erro_do_laboratorio'][-1500:]}\n```")
            else:
                cs = r.get("cenarios", {})
                cells, versao = [cell(cs.get(k)) for k, _ in COLUNAS], short(r.get("versao") or "?", 6)
                for k, label in COLUNAS:
                    c = cs.get(k) or {}
                    if c.get("status") == "falha":
                        falhas += 1
                    if c.get("status") == "ambiente":
                        avisos.append(f"{SOS[so]} / {NOMES[nav]} / {label}: {c.get('motivo')}")
                    detalhes.append(f"- {SOS[so]} / {NOMES[nav]} / {label}: {c.get('status')} | "
                                    + (str(c.get("motivo"))[:400] if c.get("status") != "ok" else "; ".join(c.get("passos", []))[:400]))
            lines.append("| " + " | ".join([SOS[so], NOMES[nav], versao] + cells) + " |")
    text = "## Laboratório de navegadores: painel real\n\n" + "\n".join(lines) + "\n"
    if avisos:
        text += "\n**Avisos (AMBIENTE depois de 2 tentativas, não reprovam):**\n" + "\n".join(f"- {a}" for a in avisos) + "\n"
    text += f"\n{falhas} cenário(s) com ❌.\n\n<details><summary>Detalhes</summary>\n\n" + "\n".join(detalhes) + "\n\n</details>\n"
    Path(out).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
