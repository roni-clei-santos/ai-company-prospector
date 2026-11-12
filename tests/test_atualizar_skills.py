"""Tests for scripts/atualizar_skills.py (links on macOS/Linux, copies on Windows or with --copy)."""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import atualizar_skills as au  # noqa: E402


@pytest.fixture
def env(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    for name in ("skill-a", "skill-b", "_shared"):
        (repo / "skills" / name).mkdir(parents=True)
        (repo / "skills" / name / "SKILL.md").write_text(f"# {name} v1\n", encoding="utf-8")
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setattr(au, "REPO", repo)
    monkeypatch.setattr(au, "project_skills", lambda repo_=repo: sorted(
        p for p in (repo / "skills").iterdir() if not p.name.startswith("_")))
    return repo, home / ".claude" / "skills"


def test_skips_shared_and_lists_skills():
    names = [p.name for p in au.project_skills(REPO)]
    assert "next-companies" in names and "build-company-list" in names and "painel" in names
    assert not any(n.startswith("_") for n in names)


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks need special permission on Windows")
def test_links_are_idempotent(env):
    repo, skills = env
    assert au.main([]) == 0
    assert au.main([]) == 0
    for name in ("skill-a", "skill-b"):
        assert (skills / name).is_symlink()
        assert (skills / name).resolve() == (repo / "skills" / name).resolve()
    assert not (skills / "_shared").exists()


def test_copy_mode_writes_marker_and_updates_after_pull(env):
    repo, skills = env
    assert au.main(["--copy"]) == 0
    target = skills / "skill-a"
    assert not target.is_symlink() and (target / "SKILL.md").read_text(encoding="utf-8") == "# skill-a v1\n"
    assert (target / au.MARKER).read_text(encoding="utf-8").strip() == str(repo)
    (repo / "skills" / "skill-a" / "SKILL.md").write_text("# skill-a v2\n", encoding="utf-8")  # git pull
    assert au.main(["--copy"]) == 0
    assert (target / "SKILL.md").read_text(encoding="utf-8") == "# skill-a v2\n"
    assert not (skills.parent / "skills.backup").exists()  # our own copy is replaced, not backed up


def test_foreign_folder_is_backed_up(env):
    repo, skills = env
    (skills / "skill-a").mkdir(parents=True)
    (skills / "skill-a" / "SKILL.md").write_text("someone else's skill\n", encoding="utf-8")
    assert au.main(["--copy"]) == 0
    backups = list((skills.parent / "skills.backup").iterdir())
    assert len(backups) == 1 and backups[0].name.startswith("skill-a.backup-")
    assert (backups[0] / "SKILL.md").read_text(encoding="utf-8") == "someone else's skill\n"
    assert (skills / "skill-a" / au.MARKER).is_file()
