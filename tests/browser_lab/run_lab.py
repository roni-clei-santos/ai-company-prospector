#!/usr/bin/env python3
"""Browser lab: the REAL panel (painel/index.html + scripts/servidor_painel.py) over a fictitious project,
in real headed browsers (Selenium 4). Runs ONLY in GitHub Actions (.github/workflows/browser-lab.yml).

Scenarios (each one in a fresh project and, where the browser allows it, a fresh profile):
  A  file:// with the server ON:  Feito records, Desfazer reverts, "Relatório da empresa" opens
  B  file:// with the server OFF: Feito shows "Vou salvar..."; server on + reload -> recorded in <= 15 s
  C  http://127.0.0.1:          Feito, Desfazer and "Relatório da empresa"
  D  audit of every clickable element of tests/browser_lab/inventario.md (http)
Safari: its WebDriver does not open file:// pages, so A and B open the page with `open -a Safari` and
drive it with AppleScript ("do JavaScript"); C and D use safaridriver.

Status: "ok", "falha" (the browser/panel failed) or "ambiente" (the test could not run). An "ambiente"
scenario runs once more; if it persists it is a warning. Exit code 1 if any scenario failed or the lab
itself broke, else 0. Writes <out>/results.json and screenshots <so>-<navegador>-<cenario>.png.
Usage: python tests/browser_lab/run_lab.py --so macos --browsers safari,chrome,edge,firefox,brave --out results
"""
import argparse
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.request
import zipfile
from pathlib import Path

import selenium
from selenium import webdriver
from selenium.common.exceptions import (ElementClickInterceptedException, ElementNotInteractableException,
                                        JavascriptException, StaleElementReferenceException, WebDriverException)
from selenium.webdriver.common.by import By

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "scripts"))
import projeto_lab  # noqa: E402

SYSTEM = platform.system()  # Darwin / Windows / Linux
SCENARIOS = ("A", "B", "C", "D")
STEP = 15            # seconds: the longest wait of any step (page, server, Feito, Desfazer)
SERVER_WAIT = 10     # seconds for the server to answer /api/estado; otherwise the whole job stops
HEADLESS = False     # --headless (quick mode only)
QUEUE_KEY = "painel-fila-v1"


class Ambiente(Exception):
    """The test could not run (driver, browser, permission of the runner): not a browser result."""


class Falha(Exception):
    """The panel did not do what it should."""


class ServidorNaoSubiu(Exception):
    """scripts/servidor_painel.py did not answer: stop the whole job at once (with its full output)."""


def first_line(e):
    text = str(getattr(e, "msg", None) or e).strip()
    return text.splitlines()[0][:300] if text else type(e).__name__


def wait(fn, secs, step=0.4):
    end = time.time() + secs
    last = None
    while time.time() < end:
        try:
            last = fn()
            if last:
                return last
        except (WebDriverException, IndexError, KeyError, ValueError, OSError):
            pass
        time.sleep(step)
    return last


# ---------------------------------------------------------------- fictitious project + real server
class Projeto:
    def __init__(self, tmp_root, nome):
        self.root = Path(tempfile.mkdtemp(prefix=f"painel-{nome}-", dir=tmp_root))
        projeto_lab.criar(self.root)
        self.env = dict(os.environ, PROSPECT_DIR=str(self.root),
                        AI_PROSPECTOR_PROJETO_ARQUIVO=str(self.root / "controle" / ".projeto-lab"))
        self.proc = None
        self.port = None
        out = subprocess.run([sys.executable, str(REPO / "scripts" / "gerar_painel.py"), "--no-open"],
                             cwd=str(self.root), env=self.env, capture_output=True, text=True, timeout=120)
        if out.returncode != 0:
            raise Ambiente(f"gerar_painel.py falhou: {(out.stderr or out.stdout)[-400:]}")
        self.index = self.root / "painel" / "index.html"

    @property
    def token(self):
        return (self.root / "controle" / ".painel-token").read_text(encoding="utf-8").strip()

    def start(self):
        self.log = self.root / "controle" / "servidor-lab.log"
        log = open(self.log, "ab")
        cmd = [sys.executable, str(REPO / "scripts" / "servidor_painel.py"), "--raiz", str(self.root)]
        t0 = time.time()
        self.proc = subprocess.Popen(cmd, cwd=str(self.root), env=self.env, stdout=log, stderr=log)

        def up():
            state = json.loads((self.root / "controle" / ".painel-servidor.json").read_text(encoding="utf-8"))
            req = urllib.request.Request(f"http://127.0.0.1:{state['porta']}/api/estado", headers={"X-Painel-Token": self.token})
            with urllib.request.urlopen(req, timeout=2) as r:
                return state["porta"] if r.status == 200 else None
        self.port = wait(up, SERVER_WAIT, step=0.2)
        log.close()
        if not self.port:
            alive = self.proc.poll() is None
            self.stop()
            raise ServidorNaoSubiu(
                f"servidor_painel.py não respondeu /api/estado em {SERVER_WAIT} s "
                f"({'processo vivo' if alive else 'processo saiu com código ' + str(self.proc_exit)})\n"
                f"comando: {cmd}\npasta: {self.root}\nPROSPECT_DIR={self.env.get('PROSPECT_DIR')}\n"
                f"--- saída do servidor ---\n{self.log.read_text(errors='replace')}")
        self.subiu_em = round(time.time() - t0, 2)
        return self.port

    proc_exit = None

    def stop(self):
        if self.proc:
            self.proc_exit = self.proc.poll()
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self.proc = None

    def progresso(self):
        return json.loads((self.root / "controle" / "progresso.json").read_text(encoding="utf-8"))

    def feitos(self):
        try:
            data = json.loads((self.root / "controle" / "painel-feitos.json").read_text(encoding="utf-8"))
        except OSError:
            return set()
        return {f["id"] for f in data.get("feitos", [])}

    @property
    def http(self):
        return f"http://127.0.0.1:{self.port}/index.html"


# ---------------------------------------------------------------- browsers on disk / drivers
def find_binary(nav):
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    local = os.environ.get("LOCALAPPDATA", "")
    cands = {
        "Darwin": {
            "safari": ["/Applications/Safari.app/Contents/MacOS/Safari"],
            "chrome": ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"],
            "edge": ["/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"],
            "firefox": ["/Applications/Firefox.app/Contents/MacOS/firefox"],
            "brave": ["/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"],
        },
        "Windows": {
            "chrome": [rf"{pf}\Google\Chrome\Application\chrome.exe", rf"{pf86}\Google\Chrome\Application\chrome.exe"],
            "edge": [rf"{pf86}\Microsoft\Edge\Application\msedge.exe", rf"{pf}\Microsoft\Edge\Application\msedge.exe"],
            "firefox": [rf"{pf}\Mozilla Firefox\firefox.exe", rf"{pf86}\Mozilla Firefox\firefox.exe"],
            "brave": [rf"{pf}\BraveSoftware\Brave-Browser\Application\brave.exe",
                      rf"{pf86}\BraveSoftware\Brave-Browser\Application\brave.exe",
                      rf"{local}\BraveSoftware\Brave-Browser\Application\brave.exe"],
        },
        "Linux": {
            "chrome": [shutil.which("google-chrome") or "", shutil.which("google-chrome-stable") or ""],
            "firefox": [shutil.which("firefox") or ""],
        },
    }.get(SYSTEM, {})
    return next((c for c in cands.get(nav, []) if c and Path(c).exists()), None)


def brave_version(binary):
    raw = ""
    if SYSTEM == "Windows":
        names = [p.name for p in Path(binary).parent.iterdir() if re.fullmatch(r"\d+\.\d+\.\d+\.\d+", p.name)]
        raw = sorted(names, key=lambda s: [int(x) for x in s.split(".")])[-1] if names else ""
    else:
        try:
            raw = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=30).stdout.strip()
        except (OSError, subprocess.SubprocessError) as e:
            raw = f"--version falhou: {e}"
    m = re.search(r"(\d+)\.(\d+)\.(\d+)\.(\d+)", raw)
    return raw, (int(m.group(1)) if m and int(m.group(1)) >= 70 else None)


def chromedriver_for(major, dest):
    plat = {"Windows": "win64", "Linux": "linux64"}.get(SYSTEM)
    if SYSTEM == "Darwin":
        plat = "mac-arm64" if platform.machine() == "arm64" else "mac-x64"
    url = "https://googlechromelabs.github.io/chrome-for-testing/latest-versions-per-milestone-with-downloads.json"
    with urllib.request.urlopen(url, timeout=60) as r:
        ms = json.loads(r.read().decode("utf-8")).get("milestones", {}).get(str(major))
    if not ms:
        raise Ambiente(f"Chrome for Testing sem chromedriver para o Chromium {major}")
    link = next((d["url"] for d in ms["downloads"].get("chromedriver", []) if d["platform"] == plat), None)
    if not link:
        raise Ambiente(f"sem chromedriver {plat} para o Chromium {major}")
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(link, timeout=120) as r:
        (dest / "cd.zip").write_bytes(r.read())
    with zipfile.ZipFile(dest / "cd.zip") as z:
        z.extractall(dest)
    exe = next(p for p in dest.rglob("chromedriver*") if p.is_file() and p.suffix in ("", ".exe"))
    exe.chmod(exe.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return str(exe), ms["version"]


class Navegador:
    def __init__(self, nav, tmp_root):
        self.nav, self.tmp_root = nav, tmp_root
        self.binary = find_binary(nav)
        self.versao = None
        self.brave_driver = None
        if not self.binary:
            raise Ambiente("não instalado")
        if nav == "brave":
            raw, major = brave_version(self.binary)
            self.brave_raw = raw
            if major is None:
                raise Ambiente(f"versão do Chromium do Brave não lida: {raw!r}")
            try:
                self.brave_driver, drv = chromedriver_for(major, Path(tmp_root) / "brave-driver")
            except Ambiente:
                raise
            except Exception as e:  # noqa: BLE001
                raise Ambiente(f"chromedriver p/ Chromium {major}: {first_line(e)}") from e
            if drv.split(".")[0] != str(major):
                raise Ambiente(f"Brave Chromium {major} x chromedriver {drv}")
        if nav == "safari":
            try:
                self.versao = subprocess.run(["defaults", "read", "/Applications/Safari.app/Contents/Info",
                                              "CFBundleShortVersionString"], capture_output=True, text=True,
                                             timeout=15).stdout.strip() or None
            except (OSError, subprocess.SubprocessError):
                pass

    def driver(self):
        """A new WebDriver session with a FRESH profile (Safari: a new session, which starts empty)."""
        nav = self.nav
        try:
            if nav in ("chrome", "edge", "brave"):
                opts = webdriver.EdgeOptions() if nav == "edge" else webdriver.ChromeOptions()
                opts.binary_location = self.binary
                profile = tempfile.mkdtemp(prefix=f"perfil-{nav}-", dir=self.tmp_root)
                for a in ("--no-first-run", "--no-default-browser-check", f"--user-data-dir={profile}", "--window-size=1280,900"):
                    opts.add_argument(a)
                if HEADLESS:
                    opts.add_argument("--headless=new")
                opts.page_load_strategy = "eager"  # do not wait for the web font of the panel
                opts.set_capability("ms:loggingPrefs" if nav == "edge" else "goog:loggingPrefs", {"browser": "ALL"})
                if nav == "edge":
                    drv = webdriver.Edge(options=opts)
                else:
                    service = webdriver.ChromeService(executable_path=self.brave_driver) if self.brave_driver else webdriver.ChromeService()
                    drv = webdriver.Chrome(options=opts, service=service)
            elif nav == "firefox":
                opts = webdriver.FirefoxOptions()
                opts.binary_location = self.binary
                opts.page_load_strategy = "eager"
                opts.add_argument("-profile")
                opts.add_argument(tempfile.mkdtemp(prefix="perfil-firefox-", dir=self.tmp_root))
                drv = webdriver.Firefox(options=opts)
                drv.set_window_size(1280, 900)
            elif nav == "safari":
                drv = webdriver.Safari()
                drv.set_window_size(1280, 900)
            else:
                raise ValueError(nav)
        except WebDriverException as e:
            raise Ambiente(f"driver não iniciou: {first_line(e)}") from e
        caps = drv.capabilities
        v = caps.get("browserVersion") or caps.get("version")
        self.versao = f"{self.brave_raw} (Chromium {v})" if nav == "brave" else (self.versao if nav == "safari" and self.versao else v)
        drv.set_page_load_timeout(STEP)
        drv.set_script_timeout(STEP)
        if HEADLESS and nav == "chrome":  # headless has no focused window: let the page use the clipboard
            try:
                drv.execute_cdp_cmd("Browser.grantPermissions", {"permissions": ["clipboardReadWrite", "clipboardSanitizedWrite"]})
            except WebDriverException:
                pass
        return drv


def quit_driver(drv):
    try:
        drv.quit()
    except Exception:  # noqa: BLE001
        pass


def screen_capture(path):
    """Whole screen (shows browser UI such as permission prompts)."""
    try:
        if SYSTEM == "Darwin":
            subprocess.run(["screencapture", "-x", str(path)], timeout=15, capture_output=True)
        elif SYSTEM == "Windows":
            ps = ("Add-Type -AssemblyName System.Windows.Forms,System.Drawing;"
                  "$b=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds;"
                  "$bmp=New-Object System.Drawing.Bitmap $b.Width,$b.Height;"
                  "$g=[System.Drawing.Graphics]::FromImage($bmp);"
                  "$g.CopyFromScreen($b.Location,[System.Drawing.Point]::Empty,$b.Size);"
                  f"$bmp.Save('{path}')")
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], timeout=30, capture_output=True)
        elif shutil.which("import"):
            subprocess.run(["import", "-window", "root", str(path)], timeout=15, capture_output=True)
    except (OSError, subprocess.SubprocessError):
        pass


# ---------------------------------------------------------------- page driver (WebDriver or Safari+AppleScript)
class Pagina:
    """Uniform access to the open panel page: js(), click(css), open(url), reload()."""

    def __init__(self, drv=None):
        self.drv = drv

    def open(self, url):
        try:
            self.drv.get(url)
        except WebDriverException as e:
            raise Ambiente(f"driver não abriu {url[:60]}: {first_line(e)}") from e

    def reload(self):
        self.drv.refresh()

    def js(self, code):
        return self.drv.execute_script("return (function(){ " + code + " })()")

    def click(self, css, index=0):
        """Real (native) click. The page redraws itself after talking to the server, so the element is
        looked up again on every try; the scroll is instant (the panel scrolls smoothly by default)."""
        last = f"não achei {css}"
        for _ in range(5):
            els = self.drv.find_elements(By.CSS_SELECTOR, css)
            if len(els) <= index:
                time.sleep(0.4)
                continue
            try:
                self.drv.execute_script("arguments[0].scrollIntoView({block:'center', behavior:'instant'})", els[index])
                time.sleep(0.1)
                els[index].click()
                return
            except (StaleElementReferenceException, ElementClickInterceptedException, ElementNotInteractableException) as e:
                last = first_line(e)
                time.sleep(0.4)
        raise Falha(f"clique em {css} falhou: {last}")

    def shot(self, path):
        try:
            self.drv.save_screenshot(str(path))
        except Exception:  # noqa: BLE001
            screen_capture(path)

    def console(self, nav):
        if nav not in ("chrome", "edge", "brave"):
            return None
        try:
            return [f"{e.get('level')}: {e.get('message')}" for e in self.drv.get_log("browser")][-30:]
        except Exception:  # noqa: BLE001
            return None


class SafariApple(Pagina):
    """The user's own Safari, opened with `open -a Safari` and driven with AppleScript "do JavaScript"
    (safaridriver does not open file:// pages). Clicks are DOM clicks (element.click())."""

    def open(self, url):
        quit_safari()
        p = subprocess.run(["open", "-a", "Safari", url], capture_output=True, text=True, timeout=30)
        if p.returncode != 0:
            raise Ambiente(f"open -a Safari falhou: {(p.stderr or p.stdout).strip()[:200]}")
        if not wait(lambda: self.js("return document.readyState") in ("interactive", "complete"), STEP):
            raise Ambiente("Safari não respondeu ao AppleScript (do JavaScript): " + (self.last_error or "sem resposta"))

    last_error = ""

    def js(self, code):
        src = "JSON.stringify((function(){ " + code + " })())"
        script = 'tell application "Safari" to do JavaScript "' + src.replace("\\", "\\\\").replace('"', '\\"') + \
                 '" in current tab of front window'
        try:
            p = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=8)
        except subprocess.TimeoutExpired as e:
            raise Ambiente("AppleScript do Safari sem resposta em 8 s (permissão de automação do runner?)") from e
        if p.returncode != 0:
            SafariApple.last_error = p.stderr.strip()[:300]
            if re.search(r"Allow JavaScript from Apple Events|not allowed|Not authori[sz]ed|-1743", p.stderr, re.I):
                raise Ambiente("Safari não permite JavaScript por Apple Events: " + SafariApple.last_error)
            raise OSError(SafariApple.last_error)
        out = p.stdout.strip()
        return json.loads(out) if out and out != "missing value" else None

    def reload(self):
        self.js("location.reload(); return 1")
        time.sleep(1)

    def click(self, css, index=0):
        ok = self.js(f"const e = document.querySelectorAll({json.dumps(css)})[{index}]; if (!e) return false; "
                     "e.scrollIntoView({block:'center'}); e.click(); return true")
        if not ok:
            raise Falha(f"não achei {css}")

    def shot(self, path):
        screen_capture(path)

    def console(self, nav):
        return None


def quit_safari():
    if subprocess.run(["pgrep", "-x", "Safari"], capture_output=True).returncode != 0:
        return
    try:
        subprocess.run(["osascript", "-e", 'quit app "Safari"'], capture_output=True, timeout=15)
    except subprocess.TimeoutExpired:
        pass
    if not wait(lambda: subprocess.run(["pgrep", "-x", "Safari"], capture_output=True).returncode != 0, 10):
        subprocess.run(["pkill", "-x", "Safari"], capture_output=True)
        time.sleep(2)


# ---------------------------------------------------------------- shared checks on the panel
def panel_ready(pg, secs=STEP):
    if not wait(lambda: pg.js("return document.querySelectorAll('input[data-done]').length") > 0, secs):
        raise Falha("o painel não mostrou nenhum item com Feito")


def status_text(pg):
    return pg.js("const e = document.getElementById('acao-status'); return e && !e.hidden ? e.textContent : ''") or ""


def feito_e_desfazer(pg, proj, steps):
    """Click Feito on the first pending item, check the project; click Desfazer, check it went back."""
    before = proj.progresso()
    item = pg.js("const e = document.querySelector('input[data-done]'); return e ? e.getAttribute('data-done') : null")
    if not item:
        raise Falha("nenhum checkbox Feito")
    if pg.js("return document.querySelector('input[data-done]').disabled"):
        raise Falha("checkbox Feito desativado")
    pg.click("input[data-done]")
    if not wait(lambda: item in proj.feitos() and proj.progresso() != before, 15):
        raise Falha(f"Feito não gravou em 15 s (status: {status_text(pg)[:80]})")
    steps.append(f"Feito gravou {item}")
    undo = f'[data-undo={json.dumps(item)}]'
    if not wait(lambda: pg.js(f"return !!document.querySelector({json.dumps(undo)})"), 10):
        raise Falha("Desfazer não apareceu em Enviados hoje")
    pg.click(undo)
    if not wait(lambda: item not in proj.feitos() and proj.progresso() == before, 15):
        raise Falha("Desfazer não voltou o progresso.json em 15 s")
    steps.append("Desfazer voltou o progresso.json")


def relatorio(pg, steps, css="#pendentes a[data-relatorio]", tab=None):
    """Open a report link of the panel, check the page content, go back to the panel."""
    if tab:
        pg.js(f"location.hash = {json.dumps(tab)}; return 1")
        time.sleep(0.5)
    href = pg.js(f"const a = document.querySelector({json.dumps(css)}); return a ? a.getAttribute('href') : null")
    if not href:
        raise Falha(f"botão de relatório ausente ({css})")
    if not re.fullmatch(r"relatorios/[a-z0-9][a-z0-9-]*\.html", href):
        raise Falha(f"href do relatório inesperado: {href}")
    pg.click(css)
    ok = wait(lambda: pg.js("const h = document.querySelector('article h1'); const b = document.querySelector('.back a');"
                            "return h && b && document.querySelectorAll('article table, article li').length ? h.textContent : null"), 15)
    if not ok:
        raise Falha("a página do relatório não carregou com conteúdo")
    if pg.js("return document.querySelectorAll('article a[href^=\"javascript\"], article b').length"):
        raise Falha("relatório com link javascript: ou HTML cru")
    steps.append(f"relatório abriu: {ok[:60]}")
    pg.click(".back a")
    panel_ready(pg, 20)
    steps.append("Voltar ao painel funcionou")


# ---------------------------------------------------------------- scenarios
def cenario_a(ctx):
    proj = Projeto(ctx.tmp, "A")
    steps = []
    try:
        proj.start()
        pg = ctx.page_file()
        pg.open(proj.index.as_uri())
        panel_ready(pg)
        if not wait(lambda: "Marcou como Feito" in status_text(pg), STEP):
            raise Falha(f"o arquivo não falou com o servidor (status: {status_text(pg)[:80]!r})")
        steps.append("arquivo + servidor: online")
        feito_e_desfazer(pg, proj, steps)
        relatorio(pg, steps)
        return steps
    finally:
        ctx.finish("A")
        proj.stop()


def cenario_b(ctx):
    proj = Projeto(ctx.tmp, "B")
    steps = []
    try:
        pg = ctx.page_file()
        pg.open(proj.index.as_uri())
        panel_ready(pg)
        pg.js(f"localStorage.removeItem('{QUEUE_KEY}'); return 1")
        pg.reload()
        panel_ready(pg)
        before = proj.progresso()
        item = pg.js("return document.querySelector('input[data-done]').getAttribute('data-done')")
        if pg.js("return document.querySelector('input[data-done]').disabled"):
            raise Falha("checkbox Feito desativado sem servidor")
        pg.click("input[data-done]")
        msg = wait(lambda: status_text(pg) if "Vou salvar" in status_text(pg) else None, 12)
        if not msg:
            raise Falha(f"sem a mensagem 'Vou salvar…' (status: {status_text(pg)[:80]!r})")
        steps.append(f"sem servidor: {msg.strip()[:90]}")
        if not pg.js(f"return !!document.querySelector('[data-undo={json.dumps(item)}]')"):
            raise Falha("o item não foi para Enviados hoje na tela")
        if proj.progresso() != before:
            raise Falha("gravou sem servidor?")
        proj.start()
        pg.reload()
        if not wait(lambda: item in proj.feitos() and proj.progresso() != before, 15):
            raise Falha("ligou o servidor e recarregou: o Feito não foi salvo em 15 s")
        if not wait(lambda: pg.js(f"return JSON.parse(localStorage.getItem('{QUEUE_KEY}') || '[]').length") == 0, 10):
            raise Falha("a fila não esvaziou depois de salvar")
        steps.append(f"servidor ligado + recarregar: {item} salvo e fila vazia")
        return steps
    finally:
        ctx.finish("B")
        proj.stop()


def cenario_c(ctx):
    proj = Projeto(ctx.tmp, "C")
    steps = []
    try:
        proj.start()
        pg = ctx.page_http()
        pg.open(proj.http)
        panel_ready(pg)
        feito_e_desfazer(pg, proj, steps)
        relatorio(pg, steps)
        return steps
    finally:
        ctx.finish("C")
        proj.stop()


EXTERNAL = {"Abrir perfil", "Abrir Rascunhos do Gmail", "Abrir a vaga", "LinkedIn", "GitHub", "Dar uma estrela no projeto"}
CLASSIFY = """
const cat = el => {
  if (el.matches('nav.tabs a')) return 'aba';
  if (el.matches('button.chip[data-jump]')) return 'chip';
  if (el.matches('button[data-copy]')) return 'copiar';
  if (el.matches('details.after > summary')) return 'outra-versao';
  if (el.matches('details.seal > summary')) return 'ver-detalhes';
  if (el.matches('input[data-done]')) return 'feito';
  if (el.matches('button[data-undo]')) return 'desfazer';
  if (el.matches('#pendentes a[data-relatorio]')) return 'relatorio-empresa';
  if (el.matches('#rodada a[data-relatorio]')) return 'relatorio-rodada';
  if (el.matches('button.toggle')) return 'ver-tabela';
  if (el.matches('a[target="_blank"]')) return 'externo';
  return null;
};
return [...document.querySelectorAll('a, button, summary, input, select, textarea, [onclick], [role=button]')]
  .map(el => ({cat: cat(el), text: (el.textContent || el.value || '').trim().slice(0, 60),
               href: el.getAttribute('href'), target: el.getAttribute('target'), rel: el.getAttribute('rel'),
               html: el.outerHTML.slice(0, 120)}));
"""


def cenario_d(ctx):
    """Audit: every clickable element of every tab, header and footer (inventario.md)."""
    proj = Projeto(ctx.tmp, "D")
    steps, bad = [], []
    try:
        proj.start()
        pg = ctx.page_http()
        pg.open(proj.http)
        panel_ready(pg)
        els = pg.js(CLASSIFY)
        cats = {}
        for e in els:
            if e["cat"] is None:
                bad.append(f"clicável fora do inventário: {e['html']}")
            cats.setdefault(e["cat"], []).append(e)
        for need in ("aba", "chip", "copiar", "outra-versao", "feito", "relatorio-empresa", "relatorio-rodada", "ver-tabela", "externo"):
            if not cats.get(need):
                bad.append(f"nenhum elemento '{need}' no painel fictício")
        # external links: never clicked in CI
        for e in cats.get("externo", []):
            if e["text"] not in EXTERNAL:
                bad.append(f"link externo sem item no inventário: {e['text']!r}")
            if not re.match(r"^https://\S+$", e["href"] or ""):
                bad.append(f"{e['text']}: href não é https absoluto ({e['href']!r})")
            if e["target"] != "_blank" or "noopener" not in (e["rel"] or "").split():
                bad.append(f"{e['text']}: falta target=_blank ou rel=noopener")
        steps.append(f"{len(cats.get('externo', []))} links externos conferidos (href/target/rel)")
        # tabs
        for tab in ("rodada", "projeto", "responderam", "followups", "pendentes"):
            pg.click(f'nav.tabs a[href="#{tab}"]')
            if not wait(lambda: pg.js(f"return !document.getElementById('{tab}').hidden && "
                                      "[...document.querySelectorAll('main > section')].filter(s => !s.hidden).length === 1"), 5):
                bad.append(f"aba {tab} não abriu")
        steps.append("5 abas")
        # chips
        for target in pg.js("return [...document.querySelectorAll('button.chip[data-jump]')].map(b => b.getAttribute('data-jump'))"):
            pg.js("window.scrollTo(0, 0); return 1")
            pg.click(f'button.chip[data-jump="{target}"]')
            if not wait(lambda: pg.js(f"const r = document.getElementById('{target}').getBoundingClientRect(); "
                                      "return r.top >= -5 && r.top < window.innerHeight"), 5):
                bad.append(f"chip {target} não levou à seção")
        steps.append("chips")
        # copy (first message) + "Outra versão" + its copy
        expected = pg.js("return document.querySelector('#p-linkedin ~ .list .msg').textContent")
        pg.click("#p-linkedin ~ .list button[data-copy]")
        label = wait(lambda: pg.js("const b = document.querySelector('#p-linkedin ~ .list button[data-copy]'); "
                                   "return /Copiado|Não copiou/.test(b.textContent) ? b.textContent : null"), 3)
        if label != "Copiado ✓":
            bad.append(f"Copiar texto: {label!r}")
        clip = ctx.read_clipboard(pg)
        if clip is not None and clip != expected:
            bad.append("Copiar texto: a área de transferência não tem o texto da mensagem")
        steps.append("copiar: " + (label or "?") + ("" if clip is None else " (conferido na área de transferência)"))
        pg.click("details.after > summary")
        if not wait(lambda: pg.js("return document.querySelector('details.after').open"), 3):
            bad.append("Outra versão não abriu")
        pg.click("details.after button[data-copy]")
        if wait(lambda: pg.js("return document.querySelector('details.after button[data-copy]').textContent"), 3) not in ("Copiado ✓",):
            bad.append("Copiar da outra versão não confirmou")
        if cats.get("ver-detalhes"):
            pg.click("details.seal > summary")
            if not pg.js("return document.querySelector('details.seal').open"):
                bad.append("ver detalhes da conferência não abriu")
        # Feito / Desfazer on one item of each list
        for group in ("p-hoje", "p-linkedin", "p-emails", "p-decisoes"):
            css = f"#{group} + .list input[data-done], #{group} ~ .list input[data-done]"
            item = pg.js(f"const g = document.getElementById('{group}'); let n = g.nextElementSibling; "
                         "const e = n && n.querySelector('input[data-done]'); return e ? e.getAttribute('data-done') : null")
            if not item:
                bad.append(f"{group}: sem item com Feito")
                continue
            before = proj.progresso()
            pg.click(f'input[data-done={json.dumps(item)}]')
            if not wait(lambda: item in proj.feitos() and proj.progresso() != before, 15):
                bad.append(f"Feito em {group} não gravou")
                continue
            undo = f'[data-undo={json.dumps(item)}]'
            wait(lambda: pg.js(f"return !!document.querySelector({json.dumps(undo)})"), 10)
            pg.click(undo)
            if not wait(lambda: item not in proj.feitos() and proj.progresso() == before, 15):
                bad.append(f"Desfazer em {group} não voltou")
            panel_ready(pg)
        steps.append("Feito + Desfazer em Fazer hoje, LinkedIn, E-mails e Decisões")
        # charts: Ver tabela / Ver gráfico
        pg.click('nav.tabs a[href="#projeto"]')
        n = pg.js("return document.querySelectorAll('#projeto button.toggle').length")
        for i in range(n):
            pg.click("#projeto button.toggle", i)
            if not pg.js(f"const c = document.querySelectorAll('#projeto button.toggle')[{i}].closest('.card'); "
                         "return c.classList.contains('show-table') && c.querySelector('.tbl-view table').offsetHeight > 0"):
                bad.append(f"Ver tabela {i + 1} não mostrou a tabela")
            pg.click("#projeto button.toggle", i)
            if pg.js(f"return document.querySelectorAll('#projeto button.toggle')[{i}].closest('.card').classList.contains('show-table')"):
                bad.append(f"Ver gráfico {i + 1} não voltou")
        steps.append(f"{n} botões Ver tabela")
        # reports: company (Pendentes) and round (Última rodada)
        pg.click('nav.tabs a[href="#pendentes"]')
        try:
            relatorio(pg, steps)
            relatorio(pg, steps, "#rodada a[data-relatorio]", tab="#rodada")
        except Falha as e:
            bad.append(str(e))
        if bad:
            raise Falha("; ".join(bad))
        return steps
    finally:
        ctx.finish("D")
        proj.stop()


# ---------------------------------------------------------------- per browser
class Ctx:
    def __init__(self, so, nav, out, tmp, browser):
        self.so, self.nav, self.out, self.tmp, self.browser = so, nav, Path(out), tmp, browser
        self.pg = None

    def page_file(self):
        if self.nav == "safari":
            if getattr(self.browser, "apple_off", None):
                raise Ambiente(self.browser.apple_off)
            self.pg = SafariApple()
        else:
            self.pg = Pagina(self.browser.driver())
        return self.pg

    def page_http(self):
        self.pg = Pagina(self.browser.driver())
        return self.pg

    def read_clipboard(self, pg):
        """Text in the clipboard when the browser lets the page read it (None otherwise)."""
        if isinstance(pg, SafariApple) or not pg.drv:
            return None
        try:
            return pg.drv.execute_async_script(
                "const done = arguments[arguments.length - 1];"
                "if (!navigator.clipboard || !navigator.clipboard.readText) return done(null);"
                "navigator.clipboard.readText().then(done, () => done(null)); setTimeout(() => done(null), 3000);")
        except WebDriverException:
            return None

    def finish(self, cenario):
        pg = self.pg
        if not pg:
            return
        self.last_shot = f"{self.so}-{self.nav}-{cenario}.png"
        pg.shot(self.out / self.last_shot)
        self.last_console = pg.console(self.nav)
        if pg.drv:
            quit_driver(pg.drv)
        elif isinstance(pg, SafariApple):
            quit_safari()
        self.pg = None


def run_scenario(fn, ctx):
    t0 = time.time()
    ctx.last_shot, ctx.last_console = None, None
    try:
        steps = fn(ctx)
        res = {"status": "ok", "motivo": "", "passos": steps}
    except Falha as e:
        res = {"status": "falha", "motivo": str(e)}
    except Ambiente as e:
        res = {"status": "ambiente", "motivo": str(e)}
        if ctx.nav == "safari" and ("AppleScript" in str(e) or "Apple Events" in str(e)):
            ctx.browser.apple_off = str(e)
    except JavascriptException as e:  # the page did not have what the step expected
        res = {"status": "falha", "motivo": f"erro na página: {first_line(e)}"}
    except WebDriverException as e:
        res = {"status": "ambiente", "motivo": f"WebDriver: {first_line(e)}"}
    except (OSError, subprocess.SubprocessError) as e:  # osascript / runner
        res = {"status": "ambiente", "motivo": f"{type(e).__name__}: {first_line(e)}"}
    res.update({"segundos": round(time.time() - t0, 1), "screenshot": ctx.last_shot, "console": ctx.last_console})
    return res


def run_browser(nav, so, out, tmp):
    res = {"so": so, "navegador": nav, "versao": None, "cenarios": {}}
    try:
        browser = Navegador(nav, tmp)
    except Ambiente as e:
        res["cenarios"] = {c: {"status": "ambiente", "motivo": str(e)} for c in SCENARIOS}
        return res
    ctx = Ctx(so, nav, out, tmp, browser)
    for name, fn in zip(SCENARIOS, (cenario_a, cenario_b, cenario_c, cenario_d)):
        r = run_scenario(fn, ctx)
        if r["status"] == "ambiente" and not getattr(browser, "apple_off", None):  # one more try; then a warning
            first = r["motivo"]
            r = run_scenario(fn, ctx)
            r["tentativas"] = 2
            if r["status"] == "ambiente":
                r["aviso"] = True
                r["primeira_tentativa"] = first
        if r["status"] == "ambiente":
            r["aviso"] = True
        res["cenarios"][name] = r
        print(f"   {name}: {r['status']} {r.get('motivo', '')[:160]}", flush=True)
    res["versao"] = browser.versao
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description="Laboratório de navegadores do painel (só no GitHub Actions).")
    ap.add_argument("--so", required=True)
    ap.add_argument("--browsers", required=True)
    ap.add_argument("--out", default="results")
    ap.add_argument("--modo", default="completo", choices=("rapido", "completo"))
    ap.add_argument("--headless", action="store_true", help="sem janela (só no modo rápido)")
    args = ap.parse_args(argv)
    global HEADLESS
    HEADLESS = args.headless
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="browser-lab-")
    results = {"so": args.so, "modo": args.modo, "headless": HEADLESS, "plataforma": platform.platform(),
               "maquina": platform.machine(), "python": sys.version.split()[0], "selenium": selenium.__version__,
               "navegadores": []}
    failed = False
    # the server must start ONCE before anything else; otherwise stop the job now, with its full output
    pre = Projeto(tmp, "preflight")
    try:
        pre.start()
        results["servidor_subiu_em_s"] = pre.subiu_em
        print(f"servidor_painel.py respondeu /api/estado em {pre.subiu_em} s (porta {pre.port})", flush=True)
    except ServidorNaoSubiu as e:
        print(str(e), flush=True)
        results["erro_servidor"] = str(e)
        (out / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
        return 1
    finally:
        pre.stop()
    for nav in [b.strip() for b in args.browsers.split(",") if b.strip()]:
        print(f"== {args.so} / {nav}", flush=True)
        try:
            r = run_browser(nav, args.so, out, tmp)
        except ServidorNaoSubiu as e:  # stop the job at once
            print(str(e), flush=True)
            results["erro_servidor"] = str(e)
            (out / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
            return 1
        except Exception:  # noqa: BLE001 - a bug in the lab itself
            r = {"so": args.so, "navegador": nav, "erro_do_laboratorio": traceback.format_exc()}
            print(r["erro_do_laboratorio"], flush=True)
        results["navegadores"].append(r)
        if r.get("erro_do_laboratorio") or any(c["status"] == "falha" for c in r.get("cenarios", {}).values()):
            failed = True
        (out / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
