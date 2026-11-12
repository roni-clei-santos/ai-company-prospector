#!/usr/bin/env python3
"""Install or update the project skills in the Claude Code skills folder (macOS, Linux and Windows).

Skills folder: <home>/.claude/skills  (~/.claude/skills on macOS/Linux, %USERPROFILE%\\.claude\\skills on Windows)

- macOS / Linux: each skill is a symbolic link to skills/<name> in this repository, so a `git pull`
  updates it with nothing else to do.
- Windows: symbolic links need special permission, so each skill is COPIED and gets a file
  `.installed-from` with the path of this repository. Run this script again after every `git pull`
  to copy the new version.

A folder with the same name that this script did not create is never overwritten: it is moved to
<home>/.claude/skills.backup/<name>.backup-YYYYMMDD first (outside the skills folder, so Claude Code
does not load two skills with the same name).

Usage (from anywhere):
  python3 scripts/atualizar_skills.py            links on macOS/Linux, copies on Windows
  python3 scripts/atualizar_skills.py --copy     force copies (any system)
  py -3 scripts\\atualizar_skills.py             (Windows)
"""
import argparse
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

MARKER = ".installed-from"
REPO = Path(__file__).resolve().parent.parent


def skills_home():
    return Path.home() / ".claude" / "skills"


def project_skills(repo=None):
    """Skill folders of the repository (skills/<name>/SKILL.md), without the shared ones (_*)."""
    base = (repo or REPO) / "skills"
    return sorted(p for p in base.iterdir() if p.is_dir() and not p.name.startswith("_") and (p / "SKILL.md").is_file())


def _backup(target, home_skills):
    backup_dir = home_skills.parent / "skills.backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / f"{target.name}.backup-{datetime.now():%Y%m%d}"
    if backup.exists():
        backup = backup.with_name(f"{backup.name}-{datetime.now():%H%M%S}")
    shutil.move(str(target), str(backup))
    return backup


def _remove(target):
    if target.is_symlink() or target.is_file():
        target.unlink()
    elif target.exists():
        shutil.rmtree(target)


def _copy(src, target, repo):
    shutil.copytree(src, target, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
    (target / MARKER).write_text(str(repo) + "\n", encoding="utf-8")


def install_skill(src, home_skills, use_copy, repo=None):
    """Install one skill. Returns a short message in Portuguese."""
    repo = repo or REPO
    target = home_skills / src.name
    if target.is_symlink():
        if use_copy:
            target.unlink()
            _copy(src, target, repo)
            return f"Skill /{src.name}: o link virou cópia ({target})"
        if Path(os.readlink(target)) != src:
            target.unlink()
            target.symlink_to(src, target_is_directory=True)
            return f"Skill /{src.name}: link atualizado"
        return f"Skill /{src.name}: link já aponta para {src}"
    note = ""
    if target.exists():
        marker = target / MARKER
        if marker.is_file():
            _remove(target)  # a copy made by this script: replace it with the current version
        else:
            note = f" (já existia uma pasta com esse nome; guardei em {_backup(target, home_skills)})"
    if use_copy:
        _copy(src, target, repo)
        return f"Skill /{src.name} copiada para {target}{note}"
    target.symlink_to(src, target_is_directory=True)
    return f"Skill /{src.name} instalada (link para {src}){note}"


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):  # Windows consoles/pipes may not be UTF-8: never crash on ✔/✘
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="Instala ou atualiza as skills do projeto no Claude Code.")
    ap.add_argument("--copy", action="store_true", help="copiar as pastas em vez de criar links (padrão no Windows)")
    args = ap.parse_args(argv)
    use_copy = args.copy or os.name == "nt"
    home_skills = skills_home()
    home_skills.mkdir(parents=True, exist_ok=True)
    for src in project_skills():
        try:
            print("✔ " + install_skill(src, home_skills, use_copy))
        except OSError as e:
            if not use_copy and getattr(e, "winerror", None) == 1314:  # Windows: no symlink privilege
                print("✔ " + install_skill(src, home_skills, True))
            else:
                print(f"✘ Skill /{src.name}: {e}", file=sys.stderr)
                return 1
    if use_copy:
        print("As skills foram COPIADAS. Depois de cada `git pull`, rode este script de novo para atualizar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
