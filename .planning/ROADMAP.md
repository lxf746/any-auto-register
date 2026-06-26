# Roadmap: Remove Electron Desktop & React UI

**Milestone:** v1.2 Remove Desktop
**Created:** 2026-06-26

## Phase Overview

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|------------------|
| 9 | Delete Desktop Code | Удалить Electron, React, PyInstaller и убрать SPA fallback | DEL-01, DEL-02, DEL-03, API-01, API-02, DOC-01, DOC-02, IGN-01, IGN-02 | 9 |
| 10 | Update CI & Docs | Убрать Electron из CI, обновить README'и | CI-01, CI-02, DOC-03, DOC-04, DOC-05 | 5 |

**Total: 2 phases | 14 requirements | All covered ✓**

## Phase Details

### Phase 9: Delete Desktop Code

**Goal:** Удалить Electron, React UI, PyInstaller и убрать SPA fallback из main.py

**Requirements:**
- DEL-01: Удалить `electron/` целиком
- DEL-02: Удалить `frontend/` целиком
- DEL-03: Удалить `pyinstaller` из `requirements.txt`
- API-01: Убрать SPA fallback блок из `main.py`
- API-02: Убрать неиспользуемые импорты `FileResponse`, `StaticFiles`
- DOC-01: Убрать Node.js build stage из `Dockerfile`
- DOC-02: Убрать копирование static из `Dockerfile`
- IGN-01: Убрать frontend/electron записи из `.gitignore`
- IGN-02: Убрать frontend/electron записи из `.dockerignore`

**Success criteria:**
1. `ls electron/` и `ls frontend/` возвращают ошибку (не существуют)
2. `grep -r "pyinstaller" requirements.txt` не находит результатов
3. `main.py` не содержит SPA fallback и не импортирует `FileResponse`/`StaticFiles`
4. `Dockerfile` не содержит `node:20` stage и не копирует `static/`
5. `.gitignore` и `.dockerignore` не содержат frontend/electron записей

**Files to modify/delete:**
- `electron/` — удалить
- `frontend/` — удалить
- `requirements.txt` — удалить pyinstaller
- `main.py` — удалить SPA fallback + импорты
- `Dockerfile` — удалить Node build stage
- `.gitignore` — удалить frontend/electron записи
- `.dockerignore` — удалить frontend/electron записи

---

### Phase 10: Update CI & Docs

**Goal:** Убрать Electron из CI pipeline и обновить документацию

**Requirements:**
- CI-01: Убрать Electron build jobs из release.yml
- CI-02: Упростить release job (только Docker)
- DOC-03: Обновить `README.md` — убрать десктопные ссылки и electron из tree
- DOC-04: Обновить `README_en.md` — то же
- DOC-05: Обновить `README_vi.md` — то же

**Success criteria:**
1. `.github/workflows/release.yml` не содержит `build-mac` или `build-win` jobs
2. Release job не зависит от Electron artifacts
3. `README.md` не содержит ссылок на "桌面版" или electron/
4. `README_en.md` не содержит "desktop" download links
5. `README_vi.md` не содержит "desktop" download links

**Files to modify:**
- `.github/workflows/release.yml`
- `README.md`
- `README_en.md`
- `README_vi.md`

---
*Created: 2026-06-26*
