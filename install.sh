#!/usr/bin/env bash
# 一键安装（macOS / Linux）：建独立 venv → 装三个依赖 → 跑金标准自校验。
# 用法：  bash install.sh   （或 chmod +x install.sh && ./install.sh）
set -e
cd "$(dirname "$0")"   # 切到脚本所在目录，避免"在错误目录运行"

PY=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
  echo "❌ 未找到 Python，请先安装 Python 3.8–3.13：https://www.python.org/downloads/"
  exit 1
fi

echo "使用解释器：$PY"
"$PY" setup_env.py   # venv 自举 + 逐包安装 + check_env 金标准自校验
