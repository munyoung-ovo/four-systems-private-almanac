import subprocess
import sys
from pathlib import Path

PACKAGES = ["lunar_python", "iztro-py", "pyswisseph"]
LOCAL_DEPS = Path(__file__).resolve().parent / ".skill_deps"

def _pip_install(package, extra=None, local=False):
    cmd = [sys.executable, "-m", "pip", "install", package] + (extra or [])
    if local:
        cmd += ["--target", str(LOCAL_DEPS), "--no-cache-dir"]
    return subprocess.run(cmd, capture_output=True, text=True)

def install_one(package) -> bool:
    r = _pip_install(package)
    if r.returncode == 0:
        print(f"  ✅ {package}")
        return True
    r2 = _pip_install(package, ["--break-system-packages"])
    if r2.returncode == 0:
        print(f"  ✅ {package}（--break-system-packages）")
        return True
    LOCAL_DEPS.mkdir(parents=True, exist_ok=True)
    r3 = _pip_install(package, local=True)
    if r3.returncode == 0:
        print(f"  ✅ {package}（本地依赖目录）")
        return True
    print(f"  ❌ {package} 安装失败：\n{(r3.stderr or r2.stderr or r.stderr or '').strip()[:400]}")
    return False

def main():
    print("安装依赖（逐包）：")
    ok = all(install_one(p) for p in PACKAGES)
    if not ok:
        print("\n部分依赖未装上，请手动重试：")
        print(f"  {sys.executable} -m pip install {' '.join(PACKAGES)} --break-system-packages")
        sys.exit(1)

    print("\n运行 check_env.py 自校验……")
    rc = subprocess.run([sys.executable, "check_env.py"]).returncode
    sys.exit(rc)

if __name__ == "__main__":
    main()
