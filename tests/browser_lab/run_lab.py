#!/usr/bin/env python3
"""Browser lab driver (Selenium 4). Runs ONLY in GitHub Actions (.github/workflows/browser-lab.yml).

For each browser: scenarios ARQUIVO, ARQUIVO_RECARREGAR, ARQUIVO_OUTRA_PASTA, HTTP (session 1, fixed
profile), then ARQUIVO_REABRIR, HTTP_REABRIR and PAINEL_REAL_HTTP (session 2, same profile).
Writes <out>/results.json, <out>/server-log.json and screenshots <so>-<navegador>-<cenario>.png.

Status of every measure: "ok", "falha" (browser result) or "ambiente" (the test could not run).
Exit code 0 whenever it measured; != 0 only if the lab itself broke (exception in this script).
Usage: python tests/browser_lab/run_lab.py --so macos --browsers safari,chrome,edge,firefox,brave --out results
"""
import argparse
import json
import os
import platform
import re
import secrets
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import urllib.request
import zipfile
from pathlib import Path

import selenium
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PROBE = HERE / "probe"
sys.path.insert(0, str(HERE))
import probe_server  # noqa: E402

PORT = 47321
TIMEOUT = 30          # seconds per scenario
VALOR = '["teste-1"]'
SYSTEM = platform.system()  # Darwin / Windows / Linux

MEDIDAS = ("arquivo_grava", "arquivo_guarda", "arquivo_reabrir", "arquivo_outro",
           "http_grava", "http_reabrir", "painel_feito", "painel_desfazer")


class LabError(Exception):
    """The test could not run (environment), as opposed to a browser result."""


def ok(detalhe=""):
    return {"status": "ok", "motivo": "", "detalhe": detalhe}


def falha(motivo, detalhe=""):
    return {"status": "falha", "motivo": motivo, "detalhe": detalhe or motivo}


def ambiente(motivo, detalhe=""):
    return {"status": "ambiente", "motivo": motivo, "detalhe": detalhe or motivo}


def first_line(e):
    text = str(getattr(e, "msg", None) or e).strip()
    return text.splitlines()[0][:300] if text else type(e).__name__


# ---------------------------------------------------------------- browsers on disk
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
    for c in cands.get(nav, []):
        if c and Path(c).exists():
            return c
    return None


def brave_version(binary):
    """(raw version, Chromium major) read from the Brave binary on disk (e.g. '131.1.73.89' -> 131)."""
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
    major = int(m.group(1)) if m and int(m.group(1)) >= 70 else None
    return raw, major


def chromedriver_for(major, dest):
    """Download the Chrome for Testing chromedriver of this Chromium milestone. Returns (path, version)."""
    plat = {"Windows": "win64", "Linux": "linux64"}.get(SYSTEM)
    if SYSTEM == "Darwin":
        plat = "mac-arm64" if platform.machine() == "arm64" else "mac-x64"
    url = "https://googlechromelabs.github.io/chrome-for-testing/latest-versions-per-milestone-with-downloads.json"
    with urllib.request.urlopen(url, timeout=60) as r:
        data = json.loads(r.read().decode("utf-8"))
    ms = data.get("milestones", {}).get(str(major))
    if not ms:
        raise LabError(f"Chrome for Testing sem chromedriver para o Chromium {major}")
    link = next((d["url"] for d in ms["downloads"].get("chromedriver", []) if d["platform"] == plat), None)
    if not link:
        raise LabError(f"Chrome for Testing sem chromedriver {plat} para o Chromium {major}")
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    zpath = dest / "chromedriver.zip"
    with urllib.request.urlopen(link, timeout=120) as r:
        zpath.write_bytes(r.read())
    with zipfile.ZipFile(zpath) as z:
        z.extractall(dest)
    exe = next(p for p in dest.rglob("chromedriver*") if p.is_file() and p.suffix in ("", ".exe"))
    exe.chmod(exe.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return str(exe), ms["version"]


# ---------------------------------------------------------------- drivers
def start_driver(nav, profile, binary, brave_driver=None):
    if nav in ("chrome", "edge", "brave"):
        opts = webdriver.EdgeOptions() if nav == "edge" else webdriver.ChromeOptions()
        opts.binary_location = binary
        for a in ("--no-first-run", "--no-default-browser-check", f"--user-data-dir={profile}", "--window-size=1280,900"):
            opts.add_argument(a)
        opts.set_capability("ms:loggingPrefs" if nav == "edge" else "goog:loggingPrefs", {"browser": "ALL"})
        if nav == "edge":
            return webdriver.Edge(options=opts)
        service = webdriver.ChromeService(executable_path=brave_driver) if brave_driver else webdriver.ChromeService()
        return webdriver.Chrome(options=opts, service=service)
    if nav == "firefox":
        opts = webdriver.FirefoxOptions()
        opts.binary_location = binary
        opts.add_argument("-profile")
        opts.add_argument(str(profile))
        return webdriver.Firefox(options=opts)
    if nav == "safari":
        return webdriver.Safari()
    raise ValueError(f"navegador desconhecido: {nav}")


def quit_driver(drv):
    try:
        drv.quit()
    except Exception:  # noqa: BLE001 - closing a broken session is not a result
        pass


def console_logs(drv, nav):
    if nav not in ("chrome", "edge", "brave"):
        return None  # Firefox / Safari drivers have no console log API; page errors are in __lab.erros
    try:
        return [f"{e.get('level')}: {e.get('message')}" for e in drv.get_log("browser")]
    except Exception as e:  # noqa: BLE001
        return [f"(sem log: {first_line(e)})"]


def screen_capture(path):
    """Whole-screen capture (shows browser UI such as permission prompts, which WebDriver screenshots miss)."""
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


# ---------------------------------------------------------------- scenarios
class Ctx:
    def __init__(self, so, nav, out, server):
        self.so, self.nav, self.out, self.server = so, nav, Path(out), server

    def shot(self, drv, cenario):
        name = f"{self.so}-{self.nav}-{cenario}.png"
        try:
            drv.save_screenshot(str(self.out / name))
        except Exception:  # noqa: BLE001
            return None
        return name

    def posts_since(self, idx):
        with self.server.lock:
            return [e for e in self.server.entries[idx:] if e["metodo"] in ("POST", "OPTIONS")]


def page_scenario(ctx, drv, cenario, url=None, reload=False):
    """Open (or reload) a probe page and wait up to TIMEOUT s for window.__lab.fim."""
    with ctx.server.lock:
        idx = len(ctx.server.entries)
    t0 = time.time()
    res = {"cenario": cenario, "url": url or "(recarregar)"}
    try:
        drv.set_page_load_timeout(TIMEOUT)
        if reload:
            drv.refresh()
        else:
            drv.get(url)
    except WebDriverException as e:
        res.update(ambiente("driver não abriu a página", first_line(e)))
        res["screenshot"] = ctx.shot(drv, cenario)
        return res
    lab, captured = None, False
    while time.time() - t0 < TIMEOUT:
        try:
            lab = drv.execute_script("return window.__lab || null")
        except WebDriverException as e:
            res.update(ambiente("driver não leu a página", first_line(e)))
            break
        if lab and lab.get("fim"):
            break
        if not captured and time.time() - t0 > 8:  # still waiting: capture the whole screen (prompts)
            screen_capture(ctx.out / f"{ctx.so}-{ctx.nav}-{cenario}-tela.png")
            captured = True
        time.sleep(0.5)
    if not captured:
        screen_capture(ctx.out / f"{ctx.so}-{ctx.nav}-{cenario}-tela.png")
    res["lab"] = lab
    res["segundos"] = round(time.time() - t0, 1)
    res["servidor"] = ctx.posts_since(idx)
    res["screenshot"] = ctx.shot(drv, cenario)
    res["console"] = console_logs(drv, ctx.nav)
    if "status" not in res:
        res.update(ok() if lab and lab.get("fim") else falha("página não terminou em 30 s"))
    return res


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def painel_real(ctx, drv):
    """Real panel (scripts/gerar_painel.py + scripts/servidor_painel.py) over a FICTITIOUS project in a temp folder."""
    res = {"cenario": "PAINEL_REAL_HTTP"}
    tmp = Path(tempfile.mkdtemp(prefix="painel-lab-"))
    env = dict(os.environ, PROSPECT_DIR=str(tmp))
    steps = [[sys.executable, str(REPO / ".github" / "ci" / "projeto_demo.py"), str(tmp)],
             [sys.executable, str(REPO / "scripts" / "gerar_painel.py"), "--no-open"]]
    for cmd in steps:
        p = subprocess.run(cmd, cwd=str(tmp), env=env, capture_output=True, text=True, timeout=120)
        if p.returncode != 0:
            res["feito"] = res["desfazer"] = ambiente("projeto fictício não foi gerado", (p.stderr or p.stdout)[-800:])
            return res
    port = free_port()
    log = open(tmp / "servidor.log", "wb")
    proc = subprocess.Popen([sys.executable, str(REPO / "scripts" / "servidor_painel.py"), "--raiz", str(tmp),
                             "--porta", str(port)], cwd=str(tmp), env=env, stdout=log, stderr=log)
    try:
        up = False
        for _ in range(60):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/estado", timeout=1) as r:
                    up = r.status == 200
                    break
            except OSError:
                time.sleep(0.5)
        if not up:
            res["feito"] = res["desfazer"] = ambiente("servidor_painel.py não subiu")
            return res
        prog = tmp / "controle" / "progresso.json"
        load = lambda: json.loads(prog.read_text(encoding="utf-8"))  # noqa: E731
        before = load()
        url = f"http://127.0.0.1:{port}/index.html"
        res["url"] = url
        try:
            drv.set_page_load_timeout(TIMEOUT)
            drv.get(url)
        except WebDriverException as e:
            res["feito"] = res["desfazer"] = ambiente("driver não abriu o painel", first_line(e))
            return res

        def wait(fn, secs):
            end = time.time() + secs
            while time.time() < end:
                try:
                    v = fn()
                    if v:
                        return v
                except (WebDriverException, IndexError):  # IndexError: element not there yet
                    pass
                time.sleep(0.4)
            return None

        cb = wait(lambda: drv.find_elements(By.CSS_SELECTOR, "#app input[data-done], input[data-done]")[0], TIMEOUT)
        if cb is None:
            res["screenshot"] = ctx.shot(drv, "PAINEL_REAL_HTTP")
            res["feito"] = res["desfazer"] = falha("nenhum checkbox Feito na aba Pendentes")
            return res
        res["item"] = cb.get_attribute("data-done")
        res["modo_pagina"] = drv.execute_script(
            "return (document.querySelector('.mode-line')||{}).textContent || null")
        if not cb.is_enabled():
            res["screenshot"] = ctx.shot(drv, "PAINEL_REAL_HTTP")
            res["feito"] = falha("checkbox Feito desativado", res["modo_pagina"] or "")
            res["desfazer"] = falha("sem Feito, não há o que desfazer")
            return res
        drv.execute_script("arguments[0].scrollIntoView({block:'center'})", cb)
        try:
            cb.click()
        except WebDriverException as e:
            res["clique"] = f"clique nativo falhou ({first_line(e)}); clique pelo label"
            drv.execute_script("arguments[0].closest('label').click()", cb)
        undo = wait(lambda: drv.find_elements(By.CSS_SELECTOR, "[data-undo]")[0], 15)
        status_txt = drv.execute_script("return (document.getElementById('acao-status')||{}).textContent || ''")
        after = load()
        res["status_feito"] = status_txt
        res["screenshot"] = ctx.shot(drv, "PAINEL_REAL_HTTP")
        if after != before and undo is not None:
            res["feito"] = ok(f"progresso.json mudou ({len(before.get('historico', []))} -> "
                              f"{len(after.get('historico', []))} notas); {status_txt}")
        elif after == before:
            res["feito"] = falha("progresso.json não mudou", status_txt)
        else:
            res["feito"] = falha("botão Desfazer não apareceu", status_txt)
        if undo is None:
            res["desfazer"] = falha("sem botão Desfazer")
            return res
        drv.execute_script("arguments[0].scrollIntoView({block:'center'})", undo)
        try:
            undo.click()
        except WebDriverException as e:
            res["clique_desfazer"] = f"clique nativo falhou ({first_line(e)}); clique por script"
            drv.execute_script("arguments[0].click()", undo)
        wait(lambda: not drv.find_elements(By.CSS_SELECTOR, "[data-undo]"), 15)
        status_txt = drv.execute_script("return (document.getElementById('acao-status')||{}).textContent || ''")
        back = load()
        res["status_desfazer"] = status_txt
        screen_capture(ctx.out / f"{ctx.so}-{ctx.nav}-PAINEL_REAL_HTTP-tela.png")
        ctx.shot(drv, "PAINEL_REAL_HTTP-desfazer")
        res["desfazer"] = ok(status_txt) if back == before else falha("progresso.json não voltou", status_txt)
        res["console"] = console_logs(drv, ctx.nav)
        return res
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        log.close()


# ---------------------------------------------------------------- measures
def step(sc, key, posts=False):
    """Cell for one step of a page scenario."""
    if sc is None:
        return ambiente("cenário não rodou")
    if sc["status"] == "ambiente":
        return ambiente(sc["motivo"], sc["detalhe"])
    lab = sc.get("lab") or {}
    if not lab.get("fim"):
        return falha("página não terminou em 30 s", json.dumps(lab, ensure_ascii=False)[:500])
    e = lab.get(key)
    if e is None:
        return falha(f"etapa {key} não rodou")
    if not e.get("ok"):
        return falha(e.get("detalhe") or "falhou", e.get("detalhe"))
    if posts:
        got = [x for x in sc.get("servidor", []) if x["metodo"] == "POST" and x["caminho"].startswith("/feito")]
        if not any(x["status"] == 200 for x in got):
            return falha("servidor não registrou o POST", json.dumps(got, ensure_ascii=False)[:500])
        pre = [x for x in sc.get("servidor", []) if x["metodo"] == "OPTIONS"]
        return ok(f"{e.get('detalhe')}; POST 200 no servidor; preflight: {len(pre)}"
                  + (f" (Private-Network: {pre[0]['ac_request_private_network']})" if pre else ""))
    return ok(e.get("detalhe"))


def measures(sc):
    m = {}
    m["arquivo_grava"] = step(sc.get("ARQUIVO"), "gravar", posts=True)
    g = step(sc.get("ARQUIVO"), "guardar")
    r = step(sc.get("ARQUIVO_RECARREGAR"), "inicial")
    if g["status"] != "ok":
        m["arquivo_guarda"] = g
    elif r["status"] == "falha":
        m["arquivo_guarda"] = falha(f"não persistiu ao recarregar: {r['detalhe']}")
    else:
        m["arquivo_guarda"] = r if r["status"] != "ok" else ok("guardou e persistiu ao recarregar")
    m["arquivo_reabrir"] = step(sc.get("ARQUIVO_REABRIR"), "inicial")
    m["arquivo_outro"] = step(sc.get("ARQUIVO_OUTRA_PASTA"), "leitura")
    m["http_grava"] = step(sc.get("HTTP"), "gravar", posts=True)
    m["http_reabrir"] = step(sc.get("HTTP_REABRIR"), "inicial")
    p = sc.get("PAINEL_REAL_HTTP")
    m["painel_feito"] = (p or {}).get("feito") or ambiente("cenário não rodou")
    m["painel_desfazer"] = (p or {}).get("desfazer") or ambiente("cenário não rodou")
    return m


def all_env(res, motivo, detalhe=""):
    res["medidas"] = {k: ambiente(motivo, detalhe) for k in MEDIDAS}
    return res


def run_browser(nav, so, out, server, tmp_root):
    res = {"so": so, "navegador": nav, "versao": None, "cenarios": {}, "medidas": {}}
    binary = find_binary(nav)
    res["binario"] = binary
    if not binary:
        return all_env(res, "não instalado")
    brave_driver = None
    if nav == "brave":
        raw, major = brave_version(binary)
        res["versao_brave_disco"] = raw
        if major is None:
            return all_env(res, f"versão do Chromium do Brave não lida: {raw!r}")
        try:
            brave_driver, drv_ver = chromedriver_for(major, Path(tmp_root) / "brave-driver")
        except Exception as e:  # noqa: BLE001 - network / CfT problem = environment
            return all_env(res, f"chromedriver p/ Chromium {major}", f"Brave {raw}; {first_line(e)}")
        res["chromedriver"] = drv_ver
        if drv_ver.split(".")[0] != str(major):
            return all_env(res, f"Brave Chromium {major} x chromedriver {drv_ver}")

    profile = Path(tempfile.mkdtemp(prefix=f"lab-{nav}-", dir=tmp_root))
    ctx = Ctx(so, nav, out, server)
    sc = res["cenarios"]
    file_index = (PROBE / "index.html").as_uri()
    file_leitor = (PROBE / "outra-pasta" / "leitor.html").as_uri()
    http_index = f"http://127.0.0.1:{PORT}/probe/index.html"

    # session 1
    try:
        drv = start_driver(nav, profile, binary, brave_driver)
    except Exception as e:  # noqa: BLE001 - driver / browser did not start = environment
        return all_env(res, "driver não iniciou", first_line(e))
    caps = drv.capabilities
    res["versao"] = caps.get("browserVersion") or caps.get("version")
    res["driver"] = (caps.get("chrome") or caps.get("msedge") or {}).get("chromedriverVersion") \
        or (caps.get("msedge") or {}).get("msedgedriverVersion") or caps.get("moz:geckodriverVersion")
    if nav == "brave":
        res["versao"] = f"{res['versao_brave_disco']} (Chromium {res['versao']})"
    try:
        sc["ARQUIVO"] = page_scenario(ctx, drv, "ARQUIVO", file_index)
        sc["ARQUIVO_RECARREGAR"] = page_scenario(ctx, drv, "ARQUIVO_RECARREGAR", reload=True)
        sc["ARQUIVO_OUTRA_PASTA"] = page_scenario(ctx, drv, "ARQUIVO_OUTRA_PASTA", file_leitor)
        sc["HTTP"] = page_scenario(ctx, drv, "HTTP", http_index)
    finally:
        quit_driver(drv)
    time.sleep(3)  # let the browser flush its storage to the profile

    # session 2: same profile (Safari: a new session; it has no profile choice)
    try:
        drv = start_driver(nav, profile, binary, brave_driver)
    except Exception as e:  # noqa: BLE001
        for c in ("ARQUIVO_REABRIR", "HTTP_REABRIR"):
            sc[c] = {"cenario": c, **ambiente("driver não reabriu", first_line(e))}
        sc["PAINEL_REAL_HTTP"] = {"feito": ambiente("driver não reabriu", first_line(e)),
                                  "desfazer": ambiente("driver não reabriu", first_line(e))}
        res["medidas"] = measures(sc)
        return res
    try:
        sc["ARQUIVO_REABRIR"] = page_scenario(ctx, drv, "ARQUIVO_REABRIR", file_index)
        sc["HTTP_REABRIR"] = page_scenario(ctx, drv, "HTTP_REABRIR", http_index)
        sc["PAINEL_REAL_HTTP"] = painel_real(ctx, drv)
    finally:
        quit_driver(drv)
    res["medidas"] = measures(sc)
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description="Laboratório de navegadores (só no GitHub Actions).")
    ap.add_argument("--so", required=True)
    ap.add_argument("--browsers", required=True)
    ap.add_argument("--out", default="results")
    args = ap.parse_args(argv)
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    token = secrets.token_urlsafe(16)
    (PROBE / "config.js").write_text(
        "window.LAB = " + json.dumps({"url": f"http://127.0.0.1:{PORT}", "token": token}) + ";\n", encoding="utf-8")
    server = probe_server.make_server(PORT, out / "server-log.json")
    threading.Thread(target=server.serve_forever, daemon=True).start()

    results = {"so": args.so, "plataforma": platform.platform(), "maquina": platform.machine(),
               "python": sys.version.split()[0], "selenium": selenium.__version__,
               "brave_instalacao": os.environ.get("BRAVE_INSTALL", ""), "navegadores": []}
    broke = False
    tmp_root = tempfile.mkdtemp(prefix="browser-lab-")
    try:
        for nav in [b.strip() for b in args.browsers.split(",") if b.strip()]:
            print(f"== {args.so} / {nav}", flush=True)
            try:
                r = run_browser(nav, args.so, out, server, tmp_root)
            except Exception:  # noqa: BLE001 - a bug in the lab itself
                broke = True
                r = {"so": args.so, "navegador": nav, "erro_do_laboratorio": traceback.format_exc()}
                print(r["erro_do_laboratorio"], flush=True)
            results["navegadores"].append(r)
            for k, v in (r.get("medidas") or {}).items():
                print(f"   {k}: {v['status']} {v['motivo']}", flush=True)
            (out / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    finally:
        server.shutdown()
        server.server_close()
        (PROBE / "config.js").unlink(missing_ok=True)
    return 1 if broke else 0


if __name__ == "__main__":
    sys.exit(main())
