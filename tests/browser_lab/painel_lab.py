"""/painel inside the lab: runs the real scripts/gerar_painel.py (main(): data, reports, start or reuse of
the server), with webbrowser.open replaced by one that only records the URL (file in $LAB_URL_FILE), so the
lab drives its own browser to it."""
import os
import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import gerar_painel  # noqa: E402


def _record(url, *args, **kwargs):
    Path(os.environ["LAB_URL_FILE"]).write_text(url, encoding="utf-8")
    return True


webbrowser.open = _record
gerar_painel.main(sys.argv[1:])
