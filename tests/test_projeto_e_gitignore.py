"""Where the scripts find the project (so /painel works from any folder), and the personal files of
the panel that must never reach git. Fictitious folders only."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import common  # noqa: E402
import gerar_painel  # noqa: E402


def _project(folder):
    (folder / "controle").mkdir(parents=True)
    (folder / "controle" / "progresso.json").write_text(json.dumps({"empresas": [], "historico": []}), encoding="utf-8")
    return folder


def test_project_search_order(tmp_path, monkeypatch):
    env, saved, here, empty = (_project(tmp_path / "env"), _project(tmp_path / "saved"),
                               _project(tmp_path / "here"), tmp_path / "empty")
    empty.mkdir()
    common.save_project_pointer(saved)
    monkeypatch.chdir(here)
    monkeypatch.setenv("PROSPECT_DIR", str(env))
    assert common.find_project() == env.resolve()                      # 1) PROSPECT_DIR
    monkeypatch.setenv("PROSPECT_DIR", str(empty))                      # no progresso.json: skipped
    assert common.find_project() == here.resolve()                      # 2) the current folder, when it is a project
    monkeypatch.delenv("PROSPECT_DIR")
    monkeypatch.chdir(empty)
    assert common.find_project() == saved.resolve()                     # 3) from any other folder: the saved project
    common.project_pointer_file().write_text(str(empty), encoding="utf-8")
    assert common.find_project() is None


def test_scripts_never_write_into_another_project(tmp_path, monkeypatch):
    """An explicit PROSPECT_DIR (even a new project without progresso.json) or a current folder that is a
    project (or a fresh copy of the repository) wins over the saved project."""
    saved, here, new, fresh, other = (_project(tmp_path / "saved"), _project(tmp_path / "here"), tmp_path / "new",
                                      tmp_path / "fresh", tmp_path / "other")
    for d in (new, fresh, other):
        d.mkdir()
    (fresh / "perfil.local.md").write_text("perfil", encoding="utf-8")
    common.save_project_pointer(saved)
    monkeypatch.chdir(here)
    monkeypatch.setenv("PROSPECT_DIR", str(new))
    assert common.project_root() == new.resolve()
    monkeypatch.delenv("PROSPECT_DIR")
    assert common.project_root() == here.resolve()
    monkeypatch.chdir(fresh)
    assert common.project_root() == fresh.resolve()
    monkeypatch.chdir(other)
    assert common.project_root() == saved.resolve()


def test_pointer_file_default_place(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_PROSPECTOR_PROJETO_ARQUIVO")
    if os.name == "nt":
        monkeypatch.setenv("APPDATA", str(tmp_path))
        expected = tmp_path / "ai-company-prospector" / "projeto"
    else:
        monkeypatch.setenv("HOME", str(tmp_path))
        expected = tmp_path / ".config" / "ai-company-prospector" / "projeto"
    assert common.project_pointer_file() == expected
    proj = _project(tmp_path / "proj")
    assert common.save_project_pointer(proj) == expected
    assert expected.read_text(encoding="utf-8").strip() == str(proj.resolve())


def test_installer_cli_and_panel_save_the_project(tmp_path, monkeypatch):
    proj = _project(tmp_path / "proj")
    out = subprocess.run([sys.executable, str(REPO / "scripts" / "common.py"), "--gravar-projeto", str(proj)],
                         capture_output=True, text=True, env=dict(os.environ))
    assert out.returncode == 0, out.stderr
    assert common.project_pointer_file().read_text(encoding="utf-8").strip() == str(proj.resolve())
    common.project_pointer_file().unlink()
    (proj / "painel").mkdir()
    shutil.copy(REPO / "painel" / "index.html", proj / "painel" / "index.html")
    monkeypatch.chdir(proj)
    gerar_painel.main(["--no-open"])
    assert common.project_pointer_file().read_text(encoding="utf-8").strip() == str(proj.resolve())


def test_no_project_found_stops_with_message(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("PROSPECT_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as e:
        gerar_painel.main(["--no-open"])
    assert e.value.code == 1
    assert capsys.readouterr().out.strip() == "Não achei o projeto. Rode o instalador na pasta do projeto."


@pytest.mark.skipif(shutil.which("git") is None or not (REPO / ".git").exists(), reason="sem git ou fora de um repositório")
@pytest.mark.parametrize("path", ["painel/servidor.js", "painel/data.js", "painel/data.json",
                                  "painel/relatorios/001-loja-exemplo-1.html", "controle/.painel-token"])
def test_personal_panel_files_are_gitignored(path):
    out = subprocess.run(["git", "check-ignore", "-q", "--no-index", path], cwd=REPO)
    assert out.returncode == 0, f"{path} não está no .gitignore"
