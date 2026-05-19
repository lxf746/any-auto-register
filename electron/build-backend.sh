#!/bin/bash
# 将 Python 后端打包为单文件可执行程序，输出到 electron/backend/
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/../"

cd "$BACKEND_DIR"

# 定位 Playwright driver（含 node 二进制 + cli.js）。Camoufox 通过
# playwright.async_api 启动 transport，缺少这里会在 Windows 上触发 WinError 2。
PLAYWRIGHT_DRIVER_DIR="$(.venv/bin/python -c "import pathlib, playwright; print(pathlib.Path(playwright.__file__).parent / 'driver')")"
echo "[info] playwright driver: $PLAYWRIGHT_DRIVER_DIR"

echo "[1/3] 清理旧产物..."
rm -rf dist build backend.spec

echo "[2/3] 打包后端..."
.venv/bin/python -m PyInstaller --onefile --name backend \
  --add-data="platforms:platforms" \
  --add-data="core:core" \
  --add-data="api:api" \
  --add-data="services:services" \
  --add-data="providers:providers" \
  --add-data="application:application" \
  --add-data="infrastructure:infrastructure" \
  --add-data="domain:domain" \
  --add-data="static:static" \
  --add-binary="${PLAYWRIGHT_DRIVER_DIR}/node:playwright/driver" \
  --add-data="${PLAYWRIGHT_DRIVER_DIR}/package:playwright/driver/package" \
  --hidden-import=uvicorn.logging \
  --hidden-import=uvicorn.loops \
  --hidden-import=uvicorn.loops.auto \
  --hidden-import=uvicorn.protocols \
  --hidden-import=uvicorn.protocols.http \
  --hidden-import=uvicorn.protocols.http.auto \
  --hidden-import=uvicorn.protocols.websockets \
  --hidden-import=uvicorn.protocols.websockets.auto \
  --hidden-import=uvicorn.lifespan \
  --hidden-import=uvicorn.lifespan.on \
  --hidden-import=uvicorn.lifespan.off \
  --hidden-import=services.turnstile_solver.api_solver \
  --hidden-import=services.turnstile_solver.db_results \
  --hidden-import=services.turnstile_solver.browser_configs \
  --hidden-import=services.turnstile_solver.start \
  --collect-all=quart \
  --collect-all=patchright \
  --collect-all=rich \
  --collect-all=browserforge \
  --collect-all=apify_fingerprint_datapoints \
  --collect-all=camoufox \
  --collect-all=playwright \
  --collect-all=language_tags \
  --collect-all=hypercorn \
  main.py

echo "[3/3] 复制产物到 electron/backend/"
mkdir -p "$SCRIPT_DIR/backend/backend"
cp dist/backend "$SCRIPT_DIR/backend/backend/backend"

echo "完成! 可执行文件: $SCRIPT_DIR/backend/backend/backend"
ls -lh "$SCRIPT_DIR/backend/backend/backend"
