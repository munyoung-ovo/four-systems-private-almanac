from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCAL_DEPS = ROOT / ".skill_deps"

PACKAGES = ["lunar_python", "iztro-py", "pyswisseph", "pypdf", "Pillow", "pytesseract"]
MODULES = {
    "lunar_python": "lunar_python",
    "iztro-py": "iztro_py",
    "pyswisseph": "swisseph",
    "pypdf": "pypdf",
    "Pillow": "PIL",
    "pytesseract": "pytesseract",
}


if LOCAL_DEPS.is_dir():
    sys.path.insert(0, str(LOCAL_DEPS))
sys.path.insert(0, str(ROOT))


def _is_installed(package: str) -> bool:
    module = MODULES.get(package, package)
    try:
        __import__(module)
        return True
    except Exception:
        return False


def _pip_install(package: str, extra: list[str] | None = None, local: bool = False) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "pip", "install", package] + (extra or [])
    if local:
        cmd += ["--target", str(LOCAL_DEPS), "--no-cache-dir"]
    return subprocess.run(cmd, capture_output=True, text=True)


def install_one(package: str) -> bool:
    if _is_installed(package):
        print(f"  OK   {package} already available")
        return True

    result = _pip_install(package)
    if result.returncode == 0:
        print(f"  OK   {package}")
        return True

    result_break = _pip_install(package, ["--break-system-packages"])
    if result_break.returncode == 0:
        print(f"  OK   {package} (--break-system-packages)")
        return True

    LOCAL_DEPS.mkdir(parents=True, exist_ok=True)
    result_local = _pip_install(package, local=True)
    if result_local.returncode == 0:
        print(f"  OK   {package} (local .skill_deps)")
        return True

    error = (result_local.stderr or result_break.stderr or result.stderr or "").strip()
    print(f"  FAIL {package}\n{error[:400]}")
    return False


def main() -> None:
    print("Checking and installing dependencies:")
    ok = all(install_one(package) for package in PACKAGES)
    if not ok:
        print("\nSome dependencies could not be installed automatically. Manual fallback:")
        print(f"  {sys.executable} -m pip install {' '.join(PACKAGES)} --break-system-packages")
        sys.exit(1)

    print("\nRunning environment self-check...")
    rc = subprocess.run([sys.executable, "check_env.py"]).returncode
    sys.exit(rc)


if __name__ == "__main__":
    main()
