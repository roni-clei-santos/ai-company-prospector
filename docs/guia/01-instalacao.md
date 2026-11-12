# 1. Instalação

[Próximo: o perfil →](02-perfil.md)

Escolha o seu sistema. macOS e Linux usam o `install.sh`; Windows usa o `install.ps1`. Os dois instaladores são idempotentes: pode rodar de novo quando quiser, eles não estragam nada que já está pronto.

## Requisitos (todos os sistemas)

- [Claude Code](https://code.claude.com/docs/en/setup) instalado e logado, com uma conta do Claude que dê acesso ao Claude Code;
- Git;
- só para o modo "Planilha + robô" (`/next-companies`): Google Chrome com a extensão Claude in Chrome conectada ([guia do Chrome](03-chrome.md)) e uma conta no LinkedIn, logada nesse Chrome. O modo "Só a planilha" (`/build-company-list`) não precisa de LinkedIn ([os dois jeitos](04-planilha.md#dois-jeitos-de-usar)).

<details open>
<summary><b>macOS</b></summary>

Precisa do [Homebrew](https://brew.sh) (se faltar, o instalador mostra o comando oficial e para).

```bash
curl -fsSL https://claude.ai/install.sh | bash        # Claude Code, se ainda não tiver
git clone https://github.com/roni-clei-santos/ai-company-prospector.git
cd ai-company-prospector
./install.sh
```

O instalador:

1. confere o Homebrew e o `python3` (instala o Python com o Homebrew, se faltar);
2. instala `openpyxl`, `reportlab` e `pytest` só para o seu usuário (`pip install --user`);
3. instala o [RTK](https://github.com/rtk-ai/rtk) com `brew install rtk` (se ainda não tiver) e liga o RTK no Claude Code (`rtk init -g --auto-patch`), conferindo com `rtk init --show` e `rtk gain`;
4. cria os links das skills `/build-company-list` e `/next-companies` em `~/.claude/skills/` (`scripts/atualizar_skills.py`; se já existir uma pasta com o mesmo nome, ela é guardada em `~/.claude/skills.backup/<nome>.backup-AAAAMMDD`);
5. copia `perfil.example.md` para `perfil.local.md`, se ainda não existir.

![Saída do ./install.sh com dados fictícios](img/terminal-install.png)
</details>

<details>
<summary><b>Linux</b></summary>

Testado num Ubuntu 24.04 limpo. Funciona com `apt` (Debian/Ubuntu), `dnf` (Fedora/RHEL) ou `pacman` (Arch).

```bash
curl -fsSL https://claude.ai/install.sh | bash        # Claude Code, se ainda não tiver
git clone https://github.com/roni-clei-santos/ai-company-prospector.git
cd ai-company-prospector
./install.sh
```

O instalador:

1. instala `python3` e `pip` pelo gerenciador de pacotes, se faltarem (pode pedir a sua senha de `sudo`; se não reconhecer o gerenciador, mostra os pacotes necessários e para);
2. instala `openpyxl`, `reportlab` e `pytest` só para o seu usuário;
3. instala o RTK pelo script oficial (`~/.local/bin/rtk`; precisa do `curl`). Se não der, segue com o aviso "RTK não instalado: o projeto funciona, só sem a economia de tokens.";
4. cria os links das skills em `~/.claude/skills/`;
5. copia `perfil.example.md` para `perfil.local.md`, se ainda não existir.

Se o RTK foi instalado e o terminal não o encontra, acrescente `~/.local/bin` ao PATH: `echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc`.
</details>

<details>
<summary><b>Windows</b></summary>

Precisa do Python 3.9 ou mais novo: [python.org](https://www.python.org/downloads/windows/) ou `winget install Python.Python.3.12`. O instalador roda no PowerShell 5.1 e 7 e é testado a cada push no GitHub Actions; as skills ainda não foram usadas num Windows real.

```powershell
irm https://claude.ai/install.ps1 | iex                # Claude Code, se ainda não tiver
git clone https://github.com/roni-clei-santos/ai-company-prospector.git
cd ai-company-prospector
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

O instalador:

1. procura o Python (`py -3`, `python` ou `python3`); se faltar, mostra o link oficial e o comando do `winget` e para;
2. instala `openpyxl`, `reportlab` e `pytest` só para o seu usuário;
3. instala o RTK com `winget install rtk-ai.rtk`; se não der, segue com o aviso "RTK não instalado";
4. **copia** as skills para `%USERPROFILE%\.claude\skills\` (o Windows exige permissão especial para links simbólicos) e grava em cada uma o arquivo `.installed-from` com o caminho do repositório;
5. copia `perfil.example.md` para `perfil.local.md`, se ainda não existir.

**Depois de cada `git pull`**, rode `py -3 scripts\atualizar_skills.py` para copiar a versão nova das skills. Nos comandos dos guias, troque `python3` por `py -3`.
</details>

> Não use `cargo install rtk`: esse é outro pacote, com o mesmo nome.

## Conferir

```bash
python3 -m pytest                      # os testes devem passar (Windows: py -3 -m pytest)
python3 scripts/atualizar_skills.py    # mostra onde estão as skills (Windows: py -3 scripts\atualizar_skills.py)
```

[Próximo: o perfil →](02-perfil.md)
