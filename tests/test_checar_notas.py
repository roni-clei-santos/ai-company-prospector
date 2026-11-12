"""Tests for scripts/checar_notas.py: invite notes in many formats (fictitious data only)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import checar_notas  # noqa: E402

NOTE = "Oi, Recrutadora, tudo bem? Vi que você cuida de tecnologia na Loja Exemplo 1. Sou dev PHP. Fico à disposição."


def notes(text):
    return [n for _, n in checar_notas.extract_notes(text)]


def test_list_item_followed_by_quote():
    text = f"## Recrutadora Exemplo\n- Conexão: não\n- Tipo: nota de convite (110 caracteres)\n\n> {NOTE}\n"
    assert notes(text) == [NOTE]


def test_heading_any_case_with_quote():
    for heading in ("### Nota de convite", "### NOTA DE CONVITE", "## nota de convite"):
        assert notes(f"{heading}\n\n> {NOTE}\n") == [NOTE]


def test_heading_without_quote_paragraph():
    text = f"### Nota de Convite\n\n{NOTE}\n\n### Mensagem pós-aceite\n\nOutro texto.\n"
    assert notes(text) == [NOTE]


def test_code_block():
    text = f"**Nota de convite**\n\n```\n{NOTE}\n```\n"
    assert notes(text) == [NOTE]


def test_label_with_colon_then_quote():
    text = f"- Tipo: nota de convite + mensagem pós-aceite\n\nNota de convite:\n> {NOTE}\n\nMensagem para depois que aceitar:\n> Obrigado!\n"
    # both markers point to the same note: counted once
    assert notes(text) == [NOTE]


def test_inline_bold_label():
    assert notes(f"**Nota de convite:** {NOTE}\n") == [NOTE]


def test_inline_plain_label():
    assert notes(f"Nota de convite: {NOTE}\n") == [NOTE]


def test_quote_without_space_after_gt():
    assert notes(f"Tipo: nota de convite\n>{NOTE}\n") == [NOTE]


def test_missing_note_is_reported():
    text = "- Tipo: nota de convite (0 caracteres)\n\n## Próxima pessoa\n- Tipo: mensagem direta\n"
    assert notes(text) == [None]


def test_plural_mention_is_not_a_marker():
    assert notes("Todas as notas de convite têm até 200 caracteres.\n") == []


@pytest.fixture
def folder(tmp_path, monkeypatch):
    monkeypatch.setenv("PROSPECT_DIR", str(tmp_path))
    (tmp_path / "perfil.local.md").write_text('```yaml\npalavras_proibidas: ["tudo bem?"]\n```\n', encoding="utf-8")
    d = tmp_path / "rascunhos" / "linkedin"
    d.mkdir(parents=True)
    return d


def test_main_flags_long_note(folder, capsys):
    (folder / "001-loja-exemplo-1.md").write_text("### Nota de convite\n\n> " + "a" * 201 + "\n", encoding="utf-8")
    assert checar_notas.main([str(folder)]) == 1
    assert "LONGA 201" in capsys.readouterr().out


def test_main_flags_style_and_missing(folder, capsys):
    (folder / "002-loja-exemplo-2.md").write_text(f"### Nota de convite\n\n> {NOTE} — fim\n\n- Tipo: nota de convite\n", encoding="utf-8")
    assert checar_notas.main([str(folder)]) == 1
    out = capsys.readouterr().out
    assert "ESTILO" in out and "SEM NOTA" in out


def test_main_ok(folder, capsys):
    ok = NOTE.replace("tudo bem?", "tudo certo?")
    (folder / "003-loja-exemplo-3.md").write_text(f"- Tipo: nota de convite\n\n> {ok}\n", encoding="utf-8")
    assert checar_notas.main([str(folder)]) == 0
    assert capsys.readouterr().out.strip().endswith("OK")
