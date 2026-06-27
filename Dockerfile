# Stage 1: Build frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend-new/package*.json ./
RUN npm ci
COPY frontend-new/ ./
RUN npm run build

# Stage 2: Python backend + runtime environment
FROM python:3.12-slim

# System dependencies: Chromium, Xvfb, x11vnc, noVNC
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Browser runtime dependencies
    chromium chromium-driver \
    # Virtual display + VNC
    xvfb x11vnc \
    # noVNC dependencies
    novnc websockify \
    # Miscellaneous
    curl ca-certificates fonts-liberation libnss3 libatk-bridge2.0-0 \
    libdrm2 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libxkbcommon0 \
    libasound2 libpango-1.0-0 libcairo2 libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (including Solver dependencies: patchright, quart, rich)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install patchright/playwright browsers (used by Solver)
# Skip playwright download — system chromium from apt is used instead
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
# RUN playwright install --with-deps chromium

# Install camoufox browser (used by Solver's camoufox mode)
RUN python -m camoufox fetch

# Copy backend code
ARG APP_VERSION=dev
COPY . .
# Inject version number
RUN echo "__version__ = \"${APP_VERSION}\"" > core/version.py
# Remove .venv and frontend source code
RUN rm -rf .venv frontend frontend-new

# Copy frontend build artifacts
COPY --from=frontend-builder /app/frontend/.next/standalone ./frontend-standalone
COPY --from=frontend-builder /app/frontend/.next/static ./frontend-standalone/.next/static
COPY --from=frontend-builder /app/frontend/public ./frontend-standalone/public

# Startup script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# APP_PASSWORD: set at runtime via -e APP_PASSWORD=xxx
# If not set, no password protection (suitable for local use)
ENV APP_PASSWORD=""

EXPOSE 8000 3000 6080 8889

ENTRYPOINT ["/docker-entrypoint.sh"]
