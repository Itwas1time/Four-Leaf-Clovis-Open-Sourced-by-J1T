"""Build the one-download Windows edition of Clovis (11 Nov 2026).

Result: release/portable/<version>/Clovis-<version>-windows-x64.zip containing

  Clovis/
    Start Clovis.cmd     double-click: starts Clovis (or reuses a running one) and opens the browser
    README.txt           plain-language start, update and uninstall notes
    python/              python.org embeddable Python + Clovis and its dependencies, nothing else

No installer, no administrator rights, no Python on the computer. Notes and collections live in
"%USERPROFILE%\\Clovis Local" (the app's normal location), so replacing the folder with a newer
version keeps them.

Usage: python tools/build_portable_windows.py WHEEL [--python 3.13.14]
WHEEL is the verified runtime wheel from tools/build_public_release.py (runtime build).
"""
import argparse
import hashlib
import io
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
# python.org embeddable builds, pinned by version and SHA-256 (recorded on first verified download).
EMBED_SHA256 = {
    "3.13.14": "90b4e5b9898b72d744650524bff92377c367f44bd5fbd09e3148656c080ad907",
}
MAX_RELATIVE_PATH = 150  # leaves ~110 characters for wherever the person extracts the folder

LAUNCHER = r'''@echo off
title Clovis
cd /d "%~dp0"
echo.
echo   Clovis is starting. Your web browser will open at http://localhost:8050
echo   Keep this window open while you use Clovis. Close it to stop Clovis.
echo   Your notes and collections are kept in "%USERPROFILE%\Clovis Local".
echo.
"%~dp0python\python.exe" -I "%~dp0python\clovis_start.py"
if errorlevel 1 (
  echo.
  echo   Clovis stopped with an error. The message above says why.
  pause
)
'''

START = '''"""Start Clovis, or open the one that is already running (portable edition)."""
import socket
import sys
import webbrowser

URL = "http://localhost:8050"
try:
    with socket.create_connection(("127.0.0.1", 8050), timeout=1):
        print("  Clovis is already running; opening it in your browser.")
        webbrowser.open(URL)
        sys.exit(0)
except OSError:
    pass
from atlas.gui.app import main
main()
'''

README = """Clovis {version} for Windows
============================

The past of any place, free and offline.

START: double-click "Start Clovis". Your browser opens Clovis at http://localhost:8050.
       Keep the black window open while you use it; close it to stop Clovis.
       (Windows may ask whether to run it the first time: choose "More info" > "Run anyway".)

YOUR DATA: notes, photos, dig records and optional collections are saved in
       {data}
       on this computer. Nothing is sent anywhere unless you export it.

UPDATE: download the new version, extract it, and use it instead of this folder.
       Your data stays where it is.

UNINSTALL: delete this folder. To also remove your data, delete the folder above.

Optional collections (radiocarbon dates, fossil specimens, museum objects and more) can be
downloaded inside Clovis: Atlas > Manage offline collections. After that they work offline.

Source code and help: https://github.com/Itwas1time/Four-Leaf-Clovis-Open-Sourced-by-J1T
"""


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def embeddable(version, cache):
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"python-{version}-embed-amd64.zip"
    if not path.exists():
        url = f"https://www.python.org/ftp/python/{version}/{path.name}"
        with urllib.request.urlopen(url, timeout=120) as response:  # nosec B310: fixed python.org HTTPS URL
            path.write_bytes(response.read())
    digest = sha256(path.read_bytes())
    pinned = EMBED_SHA256.get(version)
    if pinned and digest != pinned:
        raise SystemExit(f"Embeddable Python {version} checksum changed: {digest}")
    print(f"embeddable Python {version}: sha256 {digest}" + ("" if pinned else "  (not yet pinned in EMBED_SHA256)"))
    return path


def build(wheel, version_py):
    wheel = Path(wheel).resolve()
    app_version = wheel.name.split("-")[1]
    out = ROOT / "release" / "portable" / app_version
    stage = out / "Clovis"
    if stage.exists():
        shutil.rmtree("\\\\?\\" + str(stage))
    python_dir = stage / "python"
    python_dir.mkdir(parents=True)
    with zipfile.ZipFile(embeddable(version_py, ROOT / "release" / "portable" / "cache")) as zipped:
        zipped.extractall(python_dir)
    tag = "".join(version_py.split(".")[:2])
    pth = python_dir / f"python{tag}._pth"
    pth.write_text(f"python{tag}.zip\n.\nLib\\site-packages\n\nimport site\n", encoding="ascii")
    major_minor = ".".join(version_py.split(".")[:2])
    subprocess.run([sys.executable, "-m", "pip", "install", "--no-cache-dir", "--disable-pip-version-check",
                    "--target", str(python_dir / "Lib" / "site-packages"), "--platform", "win_amd64",
                    "--python-version", major_minor, "--implementation", "cp", "--only-binary=:all:", str(wheel)],
                   check=True)
    (python_dir / "clovis_start.py").write_text(START, encoding="utf-8")
    (stage / "Start Clovis.cmd").write_bytes(LAUNCHER.replace("\n", "\r\n").encode("ascii"))
    (stage / "README.txt").write_bytes(README.format(version=app_version, data=r"%USERPROFILE%\Clovis Local")
                                       .replace("\n", "\r\n").encode("utf-8"))
    for cache in stage.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)
    longest = max(len(path.relative_to(out).as_posix()) for path in stage.rglob("*"))
    if longest > MAX_RELATIVE_PATH:
        raise SystemExit(f"A bundled path is {longest} characters; keep it under {MAX_RELATIVE_PATH} for Windows.")
    archive = out / f"Clovis-{app_version}-windows-x64.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zipped:
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                zipped.write(path, arcname=path.relative_to(out).as_posix())
    size = sum(path.stat().st_size for path in stage.rglob("*") if path.is_file())
    print(f"{archive}\n  download {archive.stat().st_size / 1e6:.0f} MB, installed {size / 1e6:.0f} MB, "
          f"longest path {longest} chars, sha256 {sha256(archive.read_bytes())}")
    return archive


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("wheel")
    parser.add_argument("--python", default="3.13.14")
    args = parser.parse_args()
    build(args.wheel, args.python)
