# Installer for Windows (PowerShell 5.1 and 7). Idempotent: running it twice does not break anything.
# macOS and Linux: use install.sh.
# Usage (PowerShell, in this folder):
#   powershell -ExecutionPolicy Bypass -File .\install.ps1
# 'Continue' on purpose: in Windows PowerShell 5.1, stderr from native commands (python, pip, rtk)
# becomes an error record, and 'Stop' would abort the installer. Every step checks $LASTEXITCODE instead.
$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$Repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$Packages = @('openpyxl', 'reportlab', 'pytest')

function Ok($m)   { Write-Host "[ok] $m" -ForegroundColor Green }
function Info($m) { Write-Host "-> $m" -ForegroundColor Cyan }
function Warn($m) { Write-Host "[!] $m" -ForegroundColor Yellow }
function Fail($m) { Write-Host "[x] $m" -ForegroundColor Red; exit 1 }

function Test-Cmd($name) { [bool](Get-Command $name -ErrorAction SilentlyContinue) }

Write-Host ""
Write-Host "Instalando o prospector de empresas (pasta: $Repo, sistema: Windows)"
Write-Host ""

# 1) Python 3 ----------------------------------------------------------------------
# py -3 (Python launcher) first, then python / python3. The Microsoft Store alias "python"
# opens the Store instead of running Python, so every candidate is tested with --version.
$Py = $null
foreach ($cand in @(@('py', '-3'), @('python'), @('python3'))) {
    if (-not (Test-Cmd $cand[0])) { continue }
    $exe = $cand[0]
    $pre = @($cand | Select-Object -Skip 1)
    try {
        $v = & $exe @pre -c "import sys; print(sys.version_info[0])" 2>$null
        if ("$v".Trim() -eq '3') { $Py = $cand; break }
    } catch {}
}
if (-not $Py) {
    Warn "O Python 3 não foi encontrado."
    Write-Host "  Instale pelo site oficial: https://www.python.org/downloads/windows/"
    Write-Host "  ou pelo terminal:          winget install Python.Python.3.12"
    Fail "Depois de instalar o Python, abra um PowerShell novo e rode o install.ps1 de novo."
}
$PyExe = $Py[0]
$PyPre = @($Py | Select-Object -Skip 1)
function Invoke-Py { & $PyExe @PyPre @args }
Ok ("Python encontrado (" + (Invoke-Py --version 2>&1) + ", comando: " + ($Py -join ' ') + ")")

# 2) Python packages (only for your user) --------------------------------------------
Invoke-Py -c "import openpyxl, reportlab, pytest" 2>$null
if ($LASTEXITCODE -eq 0) {
    Ok ("Pacotes Python já instalados (" + ($Packages -join ', ') + ")")
} else {
    Info ("Instalando os pacotes Python (" + ($Packages -join ', ') + ") só para o seu usuário...")
    Invoke-Py -m pip install --user --quiet @Packages
    if ($LASTEXITCODE -ne 0) { Fail "Não consegui instalar os pacotes Python. Veja o erro acima e docs/guia/07-faq-e-erros.md." }
    Invoke-Py -c "import openpyxl, reportlab, pytest" 2>$null
    if ($LASTEXITCODE -ne 0) { Fail "Os pacotes foram instalados, mas o Python não os encontra. Veja docs/guia/07-faq-e-erros.md." }
    Ok "Pacotes Python instalados"
}

# 3) RTK (official Windows method: winget install rtk-ai.rtk, README of github.com/rtk-ai/rtk)
function Test-Rtk {
    if (-not (Test-Cmd 'rtk')) { return $false }
    & rtk gain *> $null
    return ($LASTEXITCODE -eq 0)
}
if (Test-Rtk) {
    Ok "RTK já instalado"
} elseif (Test-Cmd 'winget') {
    Info "Instalando o RTK com o winget (rtk-ai.rtk)..."
    & winget install --id rtk-ai.rtk -e --accept-source-agreements --accept-package-agreements *> $null
    # winget updates PATH only for new terminals: reload it for this session
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
}
if (Test-Rtk) {
    Info "Configurando o RTK no Claude Code (rtk init -g --auto-patch)..."
    & rtk init -g --auto-patch *> $null
    if ($LASTEXITCODE -eq 0) { Ok "RTK configurado" }
    else { Warn "O RTK foi instalado, mas o 'rtk init' falhou. Veja docs/guia/07-faq-e-erros.md (seção RTK)." }
} else {
    Warn "RTK não instalado: o projeto funciona, só sem a economia de tokens."
}

# 4) Skills: copied to %USERPROFILE%\.claude\skills (symbolic links need special permission on Windows)
Invoke-Py (Join-Path $Repo 'scripts\atualizar_skills.py') --copy
if ($LASTEXITCODE -ne 0) { Fail "Não consegui copiar as skills para $env:USERPROFILE\.claude\skills." }

# 5) Project folder: /painel and the scripts find it from any folder -------------------
Invoke-Py (Join-Path $Repo 'scripts\common.py') --gravar-projeto $Repo *> $null
if ($LASTEXITCODE -eq 0) { Ok "Pasta do projeto gravada em $env:APPDATA\ai-company-prospector\projeto" }
else { Warn "Não consegui gravar o caminho do projeto em $env:APPDATA\ai-company-prospector\projeto." }

# 6) Personal profile ----------------------------------------------------------------
$Perfil = Join-Path $Repo 'perfil.local.md'
if (Test-Path -LiteralPath $Perfil) {
    Ok "perfil.local.md já existe (não mexi)"
} else {
    Copy-Item -LiteralPath (Join-Path $Repo 'perfil.example.md') -Destination $Perfil
    Ok "Criei o perfil.local.md a partir do exemplo. Preencha com os seus dados (guia: docs/guia/02-perfil.md)"
}

Write-Host ""
Write-Host "Pronto. Abra o Claude Code nesta pasta e rode /build-company-list. Para o robô, rode /chrome, entre no LinkedIn e depois /next-companies."
exit 0
