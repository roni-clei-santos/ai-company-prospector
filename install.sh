#!/usr/bin/env bash
# Installer for macOS. Idempotent: running it twice does not break anything.
# Usage: ./install.sh
set -euo pipefail

if [[ "$(uname)" != "Darwin" ]]; then
  echo "Este instalador é só para macOS por enquanto. Veja o ROADMAP."
  exit 1
fi

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$HOME/.claude/skills"
SKILLS_BACKUP_DIR="$HOME/.claude/skills.backup"
TODAY="$(date +%Y%m%d)"

ok()   { printf '\033[32m✔\033[0m %s\n' "$*"; }
info() { printf '\033[36m→\033[0m %s\n' "$*"; }
warn() { printf '\033[33m!\033[0m %s\n' "$*"; }
fail() { printf '\033[31m✘\033[0m %s\n' "$*" >&2; exit 1; }

echo
echo "Instalando o prospector de empresas (pasta: $REPO)"
echo

# 1) Homebrew ---------------------------------------------------------------
if ! command -v brew >/dev/null 2>&1; then
  warn "O Homebrew não está instalado. Instale com o comando oficial (https://brew.sh):"
  echo
  echo '  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
  echo
  fail "Depois de instalar o Homebrew, abra um terminal novo e rode ./install.sh de novo."
fi
ok "Homebrew encontrado ($(brew --version | head -1))"

# 2) Python 3 + packages ------------------------------------------------------
if ! command -v python3 >/dev/null 2>&1; then
  info "python3 não encontrado. Instalando com o Homebrew…"
  brew install python
fi
ok "Python encontrado ($(python3 --version 2>&1))"

if python3 -c "import openpyxl, reportlab, pytest" >/dev/null 2>&1; then
  ok "Pacotes Python já instalados (openpyxl, reportlab, pytest)"
else
  info "Instalando os pacotes Python (openpyxl, reportlab, pytest) só para o seu usuário…"
  if ! pip3 install --user --quiet openpyxl reportlab pytest 2>/tmp/prospector-pip.log; then
    if grep -q "externally-managed-environment" /tmp/prospector-pip.log; then
      # Homebrew Python blocks pip by default; --user keeps the install inside your home folder.
      pip3 install --user --quiet --break-system-packages openpyxl reportlab pytest
    else
      cat /tmp/prospector-pip.log >&2
      fail "Não consegui instalar os pacotes Python. Veja o erro acima e docs/guia/07-faq-e-erros.md."
    fi
  fi
  python3 -c "import openpyxl, reportlab, pytest" >/dev/null 2>&1 \
    || fail "Os pacotes foram instalados, mas o python3 não os encontra. Veja docs/guia/07-faq-e-erros.md."
  ok "Pacotes Python instalados"
fi

# 3) RTK (token-saving CLI proxy). Never `cargo install rtk`: that is a different package.
if rtk gain >/dev/null 2>&1; then
  ok "RTK já instalado ($(rtk --version 2>/dev/null || echo rtk))"
else
  info "Instalando o RTK com o Homebrew…"
  brew install rtk
fi
info "Configurando o RTK no Claude Code (rtk init -g --auto-patch)…"
rtk init -g --auto-patch >/dev/null
rtk init --show >/dev/null 2>&1 || fail "O 'rtk init --show' falhou. Veja docs/guia/07-faq-e-erros.md (seção RTK)."
rtk gain >/dev/null 2>&1 || fail "O 'rtk gain' falhou depois da instalação. Veja docs/guia/07-faq-e-erros.md (seção RTK)."
ok "RTK configurado (rtk init --show e rtk gain OK)"

# 4) Skills as symlinks in ~/.claude/skills ---------------------------------
mkdir -p "$SKILLS_DIR"
for skill_path in "$REPO"/skills/*/; do
  name="$(basename "$skill_path")"
  [[ "$name" == _* ]] && continue          # _shared is not a skill
  [[ -f "$skill_path/SKILL.md" ]] || continue
  target="$SKILLS_DIR/$name"
  if [[ -L "$target" ]]; then
    ln -sfn "${skill_path%/}" "$target"
    ok "Skill /$name: link atualizado"
    continue
  fi
  if [[ -e "$target" ]]; then
    # A real folder with the same name: keep it as <name>.backup-YYYYMMDD, outside ~/.claude/skills
    # so Claude Code does not load two skills with the same name.
    mkdir -p "$SKILLS_BACKUP_DIR"
    backup="$SKILLS_BACKUP_DIR/$name.backup-$TODAY"
    [[ -e "$backup" ]] && backup="$backup-$(date +%H%M%S)"
    mv "$target" "$backup"
    warn "Já existia uma pasta $target. Guardei em $backup"
  fi
  ln -s "${skill_path%/}" "$target"
  ok "Skill /$name instalada (link para ${skill_path%/})"
done

# 5) Personal profile ---------------------------------------------------------
if [[ -f "$REPO/perfil.local.md" ]]; then
  ok "perfil.local.md já existe (não mexi)"
else
  cp "$REPO/perfil.example.md" "$REPO/perfil.local.md"
  ok "Criei o perfil.local.md a partir do exemplo. Preencha com os seus dados (guia: docs/guia/02-perfil.md)"
fi

echo
echo "Pronto. Abra o Claude Code nesta pasta, rode /chrome, entre no LinkedIn e depois /build-company-list."
