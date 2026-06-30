import os
import sys
import subprocess

LOCAL_DEPS = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".skill_deps")
if os.path.isdir(LOCAL_DEPS) and LOCAL_DEPS not in sys.path:
    sys.path.insert(0, LOCAL_DEPS)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PYBIN = sys.executable
DEPS = [
    ("lunar_python", "lunar_python", "lunar_python"),
    ("iztro-py",     "iztro_py",     "iztro-py"),
    ("pyswisseph",   "swisseph",     "pyswisseph"),
    ("pypdf",        "pypdf",        "pypdf"),
    ("Pillow",       "PIL",          "Pillow"),
    ("pytesseract",  "pytesseract",  "pytesseract"),
]

GOLD = {
    "solar": "1995-03-12T08:30:00", "gender": "女",
    "pillars": {"year": "乙亥", "month": "己卯", "day": "壬寅", "hour": "甲辰"},
    "nakshatra": "Punarvasu",
}

def _check_dep(label, module, package):
    try:
        mod = __import__(module)
    except Exception as e:
        return False, (f"❌ {label:14} 未安装 / 导入失败：{type(e).__name__}: {e}\n"
                       f"   修复： {PYBIN} -m pip install {package}"
                       f"   （受限环境追加 --break-system-packages）")
    ver = getattr(mod, "__version__", "") or getattr(mod, "VERSION", "")
    if str(ver) in ("0.0.0", "0"):
        return False, (f"❌ {label:14} 疑似空壳（version={ver}），import 成功但无实体\n"
                       f"   修复： {PYBIN} -m pip install --force-reinstall --no-cache-dir {package}")
    return True, f"✅ {label:14} OK ({ver or 'installed'})"

def _golden_check():
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from engines.bazi import build as bazi_build
        from engines.vedic import build as vedic_build
    except Exception as e:
        return False, f"❌ 引擎导入失败：{type(e).__name__}: {e}"

    errs = []
    try:
        b = bazi_build(GOLD["solar"], GOLD["gender"])
        for k, want in GOLD["pillars"].items():
            got = b["pillars"].get(k)
            if got != want:
                errs.append(f"八字{k}柱 期望{want} 实得{got}")
    except Exception as e:
        errs.append(f"八字引擎异常：{type(e).__name__}: {e}")
    try:
        v = vedic_build(GOLD["solar"], GOLD["gender"])
        if v.get("moon_nakshatra") != GOLD["nakshatra"]:
            errs.append(f"月宿 期望{GOLD['nakshatra']} 实得{v.get('moon_nakshatra')}")
        if v.get("ayanamsa") != "Lahiri":
            errs.append(f"ayanamsa 必须 Lahiri，实得{v.get('ayanamsa')}")
    except Exception as e:
        errs.append(f"Vedic 引擎异常：{type(e).__name__}: {e}")

    if errs:
        return False, "❌ 金标准自校验未通过：\n   - " + "\n   - ".join(errs)
    return True, "✅ 金标准自校验通过（四柱 乙亥/己卯/壬寅/甲辰 · 月宿 Punarvasu · Lahiri）"

def main():
    auto_install = "--install" in sys.argv or "--auto-install" in sys.argv
    print(f"Python: {sys.version.split()[0]}  @ {PYBIN}\n")
    all_ok = True
    missing = []
    for label, module, package in DEPS:
        ok, msg = _check_dep(label, module, package)
        all_ok = all_ok and ok
        if not ok:
            missing.append(package)
        print(msg)

    if missing and auto_install:
        print("\nAuto-installing missing dependencies...")
        rc = subprocess.run([PYBIN, "install.py"]).returncode
        if rc != 0:
            sys.exit(rc)
        os.execv(PYBIN, [PYBIN, __file__])

    print()
    if all_ok:
        ok, msg = _golden_check()
        all_ok = all_ok and ok
        print(msg)
    else:
        print("⏭  依赖未齐，跳过金标准自校验（先按上方命令修复）")

    print("\n" + ("✅ 环境就绪。" if all_ok else "❌ 环境存在问题，请按上方修复命令处理。"))
    sys.exit(0 if all_ok else 1)

if __name__ == "__main__":
    main()
