"""Shared helpers for the prospecting scripts.

All scripts work on the PROJECT folder: $PROSPECT_DIR if set, otherwise the current directory.
Run them from the project folder (where perfil.local.md and controle/ live).
"""
import json
import os
import re
import tempfile
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
]

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


def project_root():
    return Path(os.environ.get("PROSPECT_DIR") or Path.cwd()).resolve()


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
