"""Fictitious project of the browser lab (Loja/Agência Exemplo N, example.com): the same data as
tests/test_pendentes.py plus the company reports cited by the panel, so every button of every tab
exists (LinkedIn with a second version, e-mail, decisions with job link and company report, due
follow-ups, replies, the round report and the charts)."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "tests"))
sys.path.insert(0, str(REPO / "scripts"))
from test_pendentes import make_project  # noqa: E402

REPORT = """# #{n} {nome}

- **Status:** RASCUNHOS_CRIADOS (dados fictícios)
- Vaga: [Vaga Exemplo](https://example.com/vagas/exemplo-{n}) e a página https://example.com/carreiras.
- Link que não pode virar link: [script](javascript:alert(1)) e <b>html cru</b>.

## Contatos

| Pessoa | Cargo | Perfil |
|---|---|---|
| Pessoa Exemplo {n} | Tech Recruiter | https://www.linkedin.com/in/pessoa-exemplo-{n}/ |

## Passos

1. Pesquisa *feita*.
2. Rascunhos criados:
   - LinkedIn
   - e-mail

> Nota: relatório de demonstração.

```
bloco de código <sem html>
```
"""


class _Env:
    """make_project() only calls monkeypatch.setenv(); the lab passes PROSPECT_DIR itself."""
    @staticmethod
    def setenv(key, value):
        pass


def criar(folder):
    folder = Path(folder)
    make_project(folder, _Env())
    for n, nome, slug in ((4, "Agência Exemplo 4", "agencia-exemplo-4"), (5, "Loja Exemplo 5", "loja-exemplo-5")):
        (folder / "relatorios" / f"{n:03d}-{slug}.md").write_text(REPORT.format(n=n, nome=nome), encoding="utf-8")
    return folder
