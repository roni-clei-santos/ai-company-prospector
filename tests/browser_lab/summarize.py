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
COLUNAS = [("arquivo_grava", "Arquivo: grava"), ("arquivo_guarda", "Arquivo: guarda clique"),
           ("arquivo_reabrir", "Arquivo: persiste ao reabrir"), ("arquivo_outro", "Arquivo: outro arquivo lê"),
           ("http_grava", "Http: grava"), ("http_reabrir", "Http: persiste ao reabrir"),
           ("painel_feito", "Painel real: Feito"), ("painel_desfazer", "Painel real: Desfazer")]


def short(text, words=8):
    w = str(text or "").replace("|", "/").replace("\n", " ").split()
    return " ".join(w[:words]) + (" …" if len(w) > words else "")


def cell(m):
    if not m:
        return "AMBIENTE (sem medida)"
    if m["status"] == "ok":
        return "✅"
    if m["status"] == "ambiente":
        return f"AMBIENTE ({short(m['motivo'], 12)})"
    return f"❌ ({short(m['motivo'])})"


def load(folder):
    found = {}
    for path in sorted(Path(folder).rglob("results.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for r in data.get("navegadores", []):
            found[(data["so"], r["navegador"])] = (data, r)
    return found


def main(folder, out):
    found = load(folder)
    head = ["SO", "Navegador", "Versão"] + [c[1] for c in COLUNAS]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    detalhes = []
    for so, navs in ESPERADO.items():
        for nav in navs:
            data, r = found.get((so, nav), (None, None))
            if r is None:
                cells = ["AMBIENTE (job sem resultados)"] * len(COLUNAS)
                versao = "?"
            elif r.get("erro_do_laboratorio"):
                cells = ["AMBIENTE (erro do laboratório)"] * len(COLUNAS)
                versao = "?"
                detalhes.append(f"- **{SOS[so]} / {NOMES[nav]}**: erro do laboratório\n```\n{r['erro_do_laboratorio'][-1500:]}\n```")
            else:
                m = r.get("medidas", {})
                cells = [cell(m.get(k)) for k, _ in COLUNAS]
                versao = short(r.get("versao") or "?", 6)
                for k, label in COLUNAS:
                    x = m.get(k) or {}
                    if x.get("status") != "ok" or x.get("detalhe"):
                        detalhes.append(f"- {SOS[so]} / {NOMES[nav]} / {label}: {x.get('status')} | "
                                        f"{str(x.get('detalhe') or x.get('motivo') or '')[:400]}")
            lines.append("| " + " | ".join([SOS[so], NOMES[nav], versao] + cells) + " |")
    text = "## Laboratório de navegadores\n\n" + "\n".join(lines) + "\n\n<details><summary>Detalhes</summary>\n\n" \
        + "\n".join(detalhes) + "\n\n</details>\n"
    Path(out).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
