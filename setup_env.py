import os
import sys
import subprocess
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(ROOT, ".venv")
PACKAGES = ["lunar_python", "iztro-py", "pyswisseph", "pypdf", "Pillow", "pytesseract"]
MIN, MAX = (3, 8), (3, 13)

def _version_ok(exe) -> bool:
    try:
        out = subprocess.run(
            [exe, "-c", "import sys;print('%d.%d' % sys.version_info[:2])"],
            capture_output=True, text=True, timeout=10)
        if out.returncode != 0:
            return False
        major, minor = (int(x) for x in out.stdout.strip().split("."))
        return MIN <= (major, minor) <= MAX
    except Exception:
        return False

def _find_interpreter() -> str:
    if _version_ok(sys.executable):
        return sys.executable
    candidates = ["python3.13", "python3.12", "python3.11", "python3.10",
                  "python3.9", "python3.8", "python3", "python"]
    for name in candidates:
        path = shutil.which(name)
        if path and _version_ok(path):
            return path
    print(f"⚠️  未找到 {MIN[0]}.{MIN[1]}–{MAX[0]}.{MAX[1]} 解释器，沿用当前：{sys.executable}")
    return sys.executable

def _venv_python() -> str:
    if os.name == "nt":
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    return os.path.join(VENV_DIR, "bin", "python")

def _run(cmd, **kw) -> int:
    print("  $", " ".join(cmd))
    return subprocess.run(cmd, **kw).returncode

def main():
    base = _find_interpreter()
    print(f"基础解释器：{base}")

    if not os.path.exists(_venv_python()):
        print(f"创建 venv → {VENV_DIR}")
        if _run([base, "-m", "venv", VENV_DIR]) != 0:
            print("❌ venv 创建失败。")
            sys.exit(1)
    else:
        print(f"venv 已存在：{VENV_DIR}")

    vpy = _venv_python()
    _run([vpy, "-m", "pip", "install", "--upgrade", "pip"])

    print("逐包安装依赖：")
    failed = []
    for pkg in PACKAGES:
        if _run([vpy, "-m", "pip", "install", pkg]) != 0:
            failed.append(pkg)
    if failed:
        print(f"❌ 以下依赖安装失败：{failed}")
        print(f"   手动重试： {vpy} -m pip install {' '.join(failed)}")
        sys.exit(1)

    print("\n运行 check_env.py 自校验（venv 内）……")
    rc = _run([vpy, os.path.join(ROOT, "check_env.py")])
    if rc == 0:
        tip = (".venv\\Scripts\\python.exe" if os.name == "nt" else ".venv/bin/python")
        print(f"\n✅ 环境就绪。今后请用：{tip} -m pytest")
    sys.exit(rc)

if __name__ == "__main__":
    main()
