"""Safety net for every test: its own "saved project" file and a temporary current folder, so no
test can read or write the real project of the computer running the tests (its
~/.config/ai-company-prospector/projeto, %APPDATA% or the repository folder itself)."""
import pytest


@pytest.fixture(autouse=True)
def _isolated_project(tmp_path_factory, monkeypatch):
    monkeypatch.setenv("AI_PROSPECTOR_PROJETO_ARQUIVO", str(tmp_path_factory.mktemp("cfg") / "projeto"))
    monkeypatch.delenv("PROSPECT_DIR", raising=False)
    monkeypatch.chdir(tmp_path_factory.mktemp("cwd"))
