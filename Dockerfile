# Stage 1: 构建前端
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python 后端 + 运行环境
FROM python:3.12-slim

# 系统依赖：Chromium、Xvfb、x11vnc、noVNC
RUN apt-get update && apt-get install -y --no-install-recommends \
    # 浏览器运行依赖
    chromium chromium-driver \
    # 虚拟显示 + VNC
    xvfb x11vnc \
    # noVNC 依赖
    novnc websockify \
    # 其他
    curl ca-certificates fonts-liberation libnss3 libatk-bridge2.0-0 \
    libdrm2 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libxkbcommon0 \
    libasound2 libpango-1.0-0 libcairo2 libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 安装 Python 依赖
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# Solver 额外依赖
RUN pip install --no-cache-dir quart rich

# 安装 patchright 浏览器（Solver 使用 patchright 而非原版 playwright）
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN python -m patchright install chromium --with-deps

# 安装 camoufox 浏览器（Solver 的 camoufox 模式使用）
RUN python -m camoufox fetch

# 复制后端代码
COPY . .
# 不需要 .venv 和 frontend 源码
RUN rm -rf .venv frontend

# 复制前端构建产物
COPY --from=frontend-builder /app/static ./static

# 启动脚本
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# APP_PASSWORD: 设置后需要密码才能访问 Web UI 和 API
# 不设置则无密码保护（适用于本地使用）
ENV APP_PASSWORD=""

EXPOSE 8000 6080 8889

ENTRYPOINT ["/docker-entrypoint.sh"]
