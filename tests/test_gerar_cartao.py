"""Tests for scripts/gerar_cartao.py: the README stats card has counts only, never names."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import gerar_cartao  # noqa: E402


def test_counts_only(tmp_path):
    (tmp_path / "controle").mkdir()
    (tmp_path / "rascunhos" / "linkedin").mkdir(parents=True)
    (tmp_path / "rascunhos" / "email").mkdir(parents=True)
    (tmp_path / "relatorios").mkdir()
    (tmp_path / "controle" / "progresso.json").write_text(json.dumps({
        "empresas": [{"numero": n, "empresa": f"Loja Exemplo {n}"} for n in (1, 2, 3)],
        "historico": [{"em": "2026-11-10", "nota": "x", "sessao": "4"}]}), encoding="utf-8")
    (tmp_path / "rascunhos" / "linkedin" / "001-loja.md").write_text(
        "## 1) Recrutadora Exemplo\n- Perfil: https://example.com/a\n\n## 2) Gerente Exemplo\n- Perfil: https://example.com/b\n",
        encoding="utf-8")
    (tmp_path / "rascunhos" / "email" / "001-loja-rh.md").write_text("Para: rh@example.com\n", encoding="utf-8")
    (tmp_path / "relatorios" / "rodada-2026-11-11.md").write_text(
        "# Rodada\n\n## Envios que encontrei (registrados)\n- Responderam em 10/11: Recrutadora Exemplo (#1) pediu o CV; "
        "Gerente Exemplo (#2) aceitou\n\n## Resumo\n", encoding="utf-8")
    numbers = gerar_cartao.collect(tmp_path)
    assert numbers == [3, 3, 2, 4]  # companies, drafts (2 LinkedIn + 1 email), replies, rounds (max sessao)
    for lang in ("pt", "en"):
        for theme in ("dark", "light"):
            svg = gerar_cartao.svg(numbers, lang, theme)
            assert "Exemplo" not in svg and "example.com" not in svg
            assert ">3<" in svg and ">4<" in svg
