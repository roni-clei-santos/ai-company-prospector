"""Shared helpers for the prospecting scripts.

All scripts work on the PROJECT folder: $PROSPECT_DIR, else the current folder when it is a project,
else the path saved in ~/.config/ai-company-prospector/projeto (Windows:
%APPDATA%\\ai-company-prospector\\projeto), so /painel works from any folder (see project_root()).

Usage: python3 scripts/common.py --gravar-projeto <folder>   save <folder> as the project (installers)
"""
import json
import os
import re
import tempfile
import unicodedata
from pathlib import Path

OFFICIAL_STATUSES = [
    "CANDIDATURA_ENVIADA",
    "RASCUNHOS_CRIADOS",
    "SEM_OPORTUNIDADE",
    "JA_CONTATADA_SEM_NOVA_ACAO",
    "NAO_ELEGIVEL",
    "PULADA_PELO_CANDIDATO",
    "DESISTENCIA_DO_CANDIDATO",
    "PRECISA_DO_CANDIDATO",
    "AGUARDANDO_RESPOSTA_CANDIDATO",
    "ERRO",
    "VAGA_GESTAO_PARA_O_CANDIDATO_DECIDIR",
    "NAO_CONTATAR",
]

# Status for a company (or, in progresso.json > nao_contatar, a person) that asked not to be contacted.
DO_NOT_CONTACT = "NAO_CONTATAR"

# Legacy status names (older versions of the project used the candidate's first name).
# Matched by prefix/suffix so no personal name has to live in the code.
_LEGACY_PATTERNS = [
    (re.compile(r"^PULADA_PELO_[A-Z]+$"), "PULADA_PELO_CANDIDATO"),
    (re.compile(r"^DESISTENCIA_DO_[A-Z]+$"), "DESISTENCIA_DO_CANDIDATO"),
    (re.compile(r"^PRECISA_DO_[A-Z]+$"), "PRECISA_DO_CANDIDATO"),
    (re.compile(r"^AGUARDANDO_RESPOSTA_[A-Z]+$"), "AGUARDANDO_RESPOSTA_CANDIDATO"),
    (re.compile(r"^VAGA_GESTAO_PARA_O_[A-Z]+_DECIDIR$"), "VAGA_GESTAO_PARA_O_CANDIDATO_DECIDIR"),
]

_DATE_IN_TEXT = re.compile(r"\(?\s*(\d{2})/(\d{2})/(\d{4})\s*\)?")


def _fold(text):
    """Lowercase, strip accents and collapse spaces (for name matching)."""
    text = unicodedata.normalize("NFKD", str(text or ""))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.lower().split())


def normalize_url(url):
    """'https://www.linkedin.com/in/Alex-Exemplo/' -> 'linkedin.com/in/alex-exemplo'."""
    u = str(url or "").strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^(www\.|[a-z]{2}\.)(?=linkedin\.com)", "", u)
    return u.split("?")[0].split("#")[0].rstrip("/")


def do_not_contact(progress):
    """Return (company_numbers, people) marked NAO_CONTATAR in a loaded progresso.json.

    company_numbers: set of ints (companies whose status is NAO_CONTATAR).
    people: list of dicts from progresso.json > nao_contatar (nome, empresa, email, linkedin_url, ...).
    """
    numbers = {int(e["numero"]) for e in progress.get("empresas", [])
               if split_status(e.get("status"))[0] == DO_NOT_CONTACT}
    return numbers, list(progress.get("nao_contatar", []))


def mentions_person(text, person):
    """True if `text` names `person` by e-mail, LinkedIn URL or full name (2+ words, accent-insensitive)."""
    low = str(text or "").lower()
    email = str(person.get("email") or "").strip().lower()
    if email and email in low:
        return True
    url = normalize_url(person.get("linkedin_url"))
    if url and re.search(re.escape(url) + r"(?![\w-])", normalize_url_text(low)):
        return True
    name = _fold(person.get("nome"))
    if len(name.split()) >= 2:
        return re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", _fold(text)) is not None
    return False


def normalize_url_text(text):
    """Normalize every LinkedIn URL inside free text so it can be compared with normalize_url()."""
    return re.sub(r"(?:https?://)?(?:www\.|[a-z]{2}\.)?linkedin\.com/[^\s)>\]\"']+",
                  lambda m: normalize_url(m.group(0)), text)


PANEL_STATE = Path("controle") / ".painel-servidor.json"   # {pid, porta, iniciado_em} of the running panel server
NO_PROJECT = "Não achei o projeto. Rode o instalador na pasta do projeto."


def project_pointer_file():
    """File with the absolute path of the project, written by the installers and by gerar_painel.py.

    ~/.config/ai-company-prospector/projeto (Windows: %APPDATA%\\ai-company-prospector\\projeto).
    """
    override = os.environ.get("AI_PROSPECTOR_PROJETO_ARQUIVO")  # tests point it to a temporary file
    if override:
        return Path(override)
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming"))
    else:
        base = Path.home() / ".config"
    return base / "ai-company-prospector" / "projeto"


def save_project_pointer(root):
    """Remember `root` as the project folder (so /painel works from any folder)."""
    path = project_pointer_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(Path(root).resolve()) + "\n", encoding="utf-8")
    except OSError:
        return None
    return path


def _project_candidates():
    env = os.environ.get("PROSPECT_DIR")
    if env:
        yield Path(env)
    yield Path.cwd()  # a project folder you are in always wins over the saved one (never the wrong project)
    try:
        saved = project_pointer_file().read_text(encoding="utf-8").strip()
        if saved:
            yield Path(saved)
    except OSError:
        pass


def find_project():
    """The first of $PROSPECT_DIR, the current folder and the saved project path
    (~/.config/ai-company-prospector/projeto) that has controle/progresso.json, or None.
    From any other folder, /painel finds the project through the saved path."""
    for cand in _project_candidates():
        try:
            if (cand / "controle" / "progresso.json").is_file():
                return cand.resolve()
        except OSError:
            continue
    return None


def _looks_like_project(folder):
    return any((folder / f).exists() for f in ("controle/progresso.json", "perfil.local.md", "scripts/gerar_painel.py"))


def project_root():
    """Project folder of every script. An explicit $PROSPECT_DIR (even a project being created) or a current
    folder that is a project (or this repository) always wins, so a script never writes into another
    project; otherwise find_project() (the saved project); otherwise the current folder."""
    env = os.environ.get("PROSPECT_DIR")
    if env:
        return Path(env).resolve()
    if _looks_like_project(Path.cwd()):
        return Path.cwd().resolve()
    return find_project() or Path.cwd().resolve()


def pid_alive(pid):
    """True if a process with this id is running (macOS, Linux and Windows)."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        ok = ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(handle)
        return bool(ok) and code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def panel_state(root):
    """{pid, porta, iniciado_em} of the panel server of this project, or None. A file left by a server that is
    no longer running (or unreadable) is deleted."""
    path = Path(root) / PANEL_STATE
    try:
        info = json.loads(path.read_text(encoding="utf-8"))
        if pid_alive(info["pid"]) and int(info["porta"]) > 0:
            return info
    except FileNotFoundError:
        return None
    except (OSError, ValueError, KeyError, TypeError):
        pass
    try:
        path.unlink()
    except OSError:
        pass
    return None


def panel_url(root, timeout=2.0):
    """http://127.0.0.1:<porta>/ of the panel server of this project when it answers /api/estado (200, same
    pid) within `timeout` seconds, else None."""
    import urllib.request
    info = panel_state(root)
    if not info:
        return None
    base = f"http://127.0.0.1:{int(info['porta'])}"
    try:
        with urllib.request.urlopen(base + "/api/estado", timeout=timeout) as r:
            if r.status == 200 and json.loads(r.read().decode("utf-8")).get("pid") == int(info["pid"]):
                return base + "/"
    except (OSError, ValueError):
        pass
    return None


def split_status(raw):
    """Split a raw status like 'PULADA_PELO_X (10/11/2026)' into (status, iso_date_or_None).

    The status name is normalized to the official list (legacy names are mapped).
    """
    if raw is None:
        return None, None
    text = str(raw).strip()
    if not text:
        return None, None
    date = None
    m = _DATE_IN_TEXT.search(text)
    if m:
        d, mo, y = m.groups()
        date = f"{y}-{mo}-{d}"
        text = (text[: m.start()] + text[m.end():]).strip()
    name = text.split()[0] if text.split() else text
    for pattern, new in _LEGACY_PATTERNS:
        if pattern.match(name):
            name = new
            break
    return name, date


def read_profile_fields(path=None):
    """Read simple top-level `key: value` fields from the yaml blocks of perfil.local.md.

    Only scalars are returned (strings/numbers); lists and nested maps are ignored.
    This avoids a PyYAML dependency.
    """
    path = Path(path) if path else project_root() / "perfil.local.md"
    if not path.exists():
        return {}
    fields = {}
    in_yaml = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("```"):
            in_yaml = line.strip() in ("```yaml", "```yml") if not in_yaml else False
            continue
        if not in_yaml:
            continue
        m = re.match(r"^([a-z_]+):\s*(.*?)\s*(#.*)?$", line)
        if not m or not m.group(2):
            continue
        value = m.group(2).strip()
        if value.startswith("[") or value.startswith("{"):
            continue
        fields[m.group(1)] = value.strip('"').strip("'")
    return fields


def find_company_sheet(root=None):
    """Return the input company spreadsheet: perfil field `planilha_empresas`, else the only empresas-*.xlsx."""
    root = Path(root) if root else project_root()
    name = read_profile_fields(root / "perfil.local.md").get("planilha_empresas")
    if name and (root / name).exists():
        return root / name
    found = sorted(root.glob("empresas-*.xlsx"))
    return found[0] if len(found) == 1 else None


def backup_file(path, keep=30):
    """Copy `path` to <its folder>/.backups/<name>-<timestamp><ext> and keep only the newest `keep` copies."""
    import shutil
    from datetime import datetime
    path = Path(path)
    if not path.exists():
        return None
    folder = path.parent / ".backups"
    folder.mkdir(exist_ok=True)
    target = folder / f"{path.stem}-{datetime.now():%Y%m%d-%H%M%S-%f}{path.suffix}"
    shutil.copy2(path, target)
    old = sorted(folder.glob(f"{path.stem}-*{path.suffix}"))
    for extra in old[:-keep]:
        extra.unlink()
    return target


def write_json_atomic(path, data):
    path = Path(path)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


def save_workbook_atomic(wb, path):
    path = Path(path)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.stem, suffix=".xlsx")
    os.close(fd)
    wb.save(tmp)
    os.replace(tmp, path)


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == "--gravar-projeto":
        saved = save_project_pointer(sys.argv[2])
        print(f"Projeto gravado em {saved}" if saved else "Não consegui gravar o caminho do projeto.")
        sys.exit(0 if saved else 1)
    print(__doc__)
    sys.exit(2)
