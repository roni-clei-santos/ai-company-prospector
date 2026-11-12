#!/usr/bin/env bash
# Installer for macOS and Linux. Idempotent: running it twice does not break anything.
# Windows: use install.ps1 (PowerShell).
# Usage: ./install.sh
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIP_PACKAGES=(openpyxl reportlab pytest)
PIP_LOG="$(mktemp "${TMPDIR:-/tmp}/prospector-pip.XXXXXX")"
trap 'rm -f "$PIP_LOG"' EXIT

ok()   { printf '\033[32m✔\033[0m %s\n' "$*"; }
info() { printf '\033[36m→\033[0m %s\n' "$*"; }
warn() { printf '\033[33m!\033[0m %s\n' "$*"; }
fail() { printf '\033[31m✘\033[0m %s\n' "$*" >&2; exit 1; }

case "$(uname -s)" in
  Darwin) OS="macos" ;;
  Linux)  OS="linux" ;;
  *)
    echo "Sistema não suportado por este instalador: $(uname -s)."
    echo "No Windows, abra o PowerShell nesta pasta e rode: powershell -ExecutionPolicy Bypass -File .\\install.ps1"
    exit 1 ;;
esac

# Run a command as root when needed (Linux package managers).
as_root() {
  if [[ "$(id -u)" -eq 0 ]]; then "$@"
  elif command -v sudo >/dev/null 2>&1; then sudo "$@"
  else fail "Preciso de permissão de administrador para: $*. Rode como root ou instale o sudo."
  fi
}

echo
echo "Instalando o prospector de empresas (pasta: $REPO, sistema: $OS)"
echo

# 1) Python 3 + pip -------------------------------------------------------------
if [[ "$OS" == "macos" ]]; then
  if ! command -v brew >/dev/null 2>&1; then
    warn "O Homebrew não está instalado. Instale com o comando oficial (https://brew.sh):"
    echo
    echo '  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
    echo
    fail "Depois de instalar o Homebrew, abra um terminal novo e rode ./install.sh de novo."
  fi
  ok "Homebrew encontrado ($(brew --version | head -1))"
  if ! command -v python3 >/dev/null 2>&1; then
    info "python3 não encontrado. Instalando com o Homebrew…"
    brew install python
  fi
else
  if ! command -v python3 >/dev/null 2>&1 || ! python3 -m pip --version >/dev/null 2>&1; then
    if command -v apt-get >/dev/null 2>&1; then
      info "Instalando python3 e pip com o apt…"
      as_root apt-get update -qq
      as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3 python3-pip >/dev/null
    elif command -v dnf >/dev/null 2>&1; then
      info "Instalando python3 e pip com o dnf…"
      as_root dnf install -y -q python3 python3-pip
    elif command -v pacman >/dev/null 2>&1; then
      info "Instalando python3 e pip com o pacman…"
      as_root pacman -Sy --noconfirm --needed python python-pip
    else
      warn "Não reconheci o gerenciador de pacotes (procurei apt, dnf e pacman)."
      echo "  Instale estes pacotes e rode ./install.sh de novo: python3 (3.9 ou mais novo) e pip para python3."
      fail "Faltam o python3 e/ou o pip."
    fi
  fi
fi
command -v python3 >/dev/null 2>&1 || fail "O python3 não foi encontrado depois da instalação."
ok "Python encontrado ($(python3 --version 2>&1))"

# 2) Python packages (only for your user) ---------------------------------------
if python3 -c "import openpyxl, reportlab, pytest" >/dev/null 2>&1; then
  ok "Pacotes Python já instalados (${PIP_PACKAGES[*]})"
else
  info "Instalando os pacotes Python (${PIP_PACKAGES[*]}) só para o seu usuário…"
  if ! python3 -m pip install --user --quiet "${PIP_PACKAGES[@]}" 2>"$PIP_LOG"; then
    if grep -q "externally-managed-environment" "$PIP_LOG"; then
      # Homebrew Python and recent Debian/Ubuntu block pip by default; --user keeps it in your home folder.
      python3 -m pip install --user --quiet --break-system-packages "${PIP_PACKAGES[@]}"
    else
      cat "$PIP_LOG" >&2
      fail "Não consegui instalar os pacotes Python. Veja o erro acima e docs/guia/07-faq-e-erros.md."
    fi
  fi
  python3 -c "import openpyxl, reportlab, pytest" >/dev/null 2>&1 \
    || fail "Os pacotes foram instalados, mas o python3 não os encontra. Veja docs/guia/07-faq-e-erros.md."
  ok "Pacotes Python instalados"
fi

# 3) RTK (token-saving CLI proxy). Never `cargo install rtk`: that is a different package.
rtk_ready() { command -v rtk >/dev/null 2>&1 && rtk gain >/dev/null 2>&1; }
[[ -x "$HOME/.local/bin/rtk" ]] && export PATH="$HOME/.local/bin:$PATH"
if rtk_ready; then
  ok "RTK já instalado ($(rtk --version 2>/dev/null || echo rtk))"
elif [[ "$OS" == "macos" ]]; then
  info "Instalando o RTK com o Homebrew…"
  brew install rtk
  rtk_ready || fail "O 'rtk gain' falhou depois da instalação. Veja docs/guia/07-faq-e-erros.md (seção RTK)."
elif command -v curl >/dev/null 2>&1; then
  # Official Linux method (README of github.com/rtk-ai/rtk): installs to ~/.local/bin
  info "Instalando o RTK com o script oficial (github.com/rtk-ai/rtk)…"
  if curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh | sh >/dev/null 2>&1; then
    export PATH="$HOME/.local/bin:$PATH"
  fi
fi
if rtk_ready; then
  info "Configurando o RTK no Claude Code (rtk init -g --auto-patch)…"
  if rtk init -g --auto-patch >/dev/null 2>&1 && rtk init --show >/dev/null 2>&1; then
    ok "RTK configurado (rtk init --show e rtk gain OK)"
  elif [[ "$OS" == "macos" ]]; then
    fail "O 'rtk init' falhou. Veja docs/guia/07-faq-e-erros.md (seção RTK)."
  else
    warn "O RTK foi instalado, mas o 'rtk init' falhou. Veja docs/guia/07-faq-e-erros.md (seção RTK)."
  fi
  if [[ "$OS" == "linux" && ":$PATH:" != *":$HOME/.local/bin:"* ]] && ! grep -qs '.local/bin' "$HOME/.profile" "$HOME/.bashrc"; then
    warn "Acrescente ~/.local/bin ao PATH (ex.: echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc)."
  fi
else
  warn "RTK não instalado: o projeto funciona, só sem a economia de tokens."
fi

# 4) Skills: symbolic links in ~/.claude/skills (same logic as scripts/atualizar_skills.py)
python3 "$REPO/scripts/atualizar_skills.py" || fail "Não consegui instalar as skills em ~/.claude/skills."

# 5) Personal profile -------------------------------------------------------------
if [[ -f "$REPO/perfil.local.md" ]]; then
  ok "perfil.local.md já existe (não mexi)"
else
  cp "$REPO/perfil.example.md" "$REPO/perfil.local.md"
  ok "Criei o perfil.local.md a partir do exemplo. Preencha com os seus dados (guia: docs/guia/02-perfil.md)"
fi

echo
echo "Pronto. Abra o Claude Code nesta pasta, rode /chrome, entre no LinkedIn e depois /build-company-list."
