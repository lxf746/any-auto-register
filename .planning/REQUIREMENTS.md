# Requirements: Remove Electron Desktop & React UI

**Defined:** 2026-06-26
**Core Value:** Убрать дублирующий код, оставить только API + Customer Portal

## v1 Requirements

### Delete Directories

- [ ] **DEL-01**: Удалить директорию `electron/` целиком
- [ ] **DEL-02**: Удалить директорию `frontend/` целиком
- [ ] **DEL-03**: Удалить `pyinstaller` из `requirements.txt`

### Modify Backend

- [ ] **API-01**: Убрать SPA fallback блок из `main.py`
- [ ] **API-02**: Убрать неиспользуемые импорты `FileResponse`, `StaticFiles` из `main.py`

### Docker & CI

- [ ] **DOC-01**: Убрать Node.js build stage из `Dockerfile`
- [ ] **DOC-02**: Убрать копирование static из `Dockerfile`
- [ ] **CI-01**: Убрать Electron build jobs из `.github/workflows/release.yml`
- [ ] **CI-02**: Упростить release job (только Docker)

### Cleanup

- [ ] **IGN-01**: Убрать frontend/electron записи из `.gitignore`
- [ ] **IGN-02**: Убрать frontend/electron записи из `.dockerignore`
- [ ] **DOC-03**: Обновить `README.md` — убрать десктопные ссылки
- [ ] **DOC-04**: Обновить `README_en.md` — убрать десктопные ссылки
- [ ] **DOC-05**: Обновить `README_vi.md` — убрать десктопные ссылки

## v2 Requirements

Deferred to future milestone.

### Refactoring

- **REF-01**: Разбить `core/account_graph.py` (1060 строк) на модули
- **REF-02**: Разбить `core/base_mailbox.py` (2059 строк) по провайдерам
- **REF-03**: Разбить `platforms/chatgpt/browser_register.py` (3908 строк) по шагам

## Out of Scope

| Feature | Reason |
|---------|--------|
| core/desktop_apps.py | Core feature — детекция локальных IDE |
| Customer Portal | Отдельное приложение |
| API endpoints | Не меняются |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DEL-01 | Phase 9 | Pending |
| DEL-02 | Phase 9 | Pending |
| DEL-03 | Phase 9 | Pending |
| API-01 | Phase 9 | Pending |
| API-02 | Phase 9 | Pending |
| DOC-01 | Phase 9 | Pending |
| DOC-02 | Phase 9 | Pending |
| CI-01 | Phase 10 | Pending |
| CI-02 | Phase 10 | Pending |
| IGN-01 | Phase 9 | Pending |
| IGN-02 | Phase 9 | Pending |
| DOC-03 | Phase 10 | Pending |
| DOC-04 | Phase 10 | Pending |
| DOC-05 | Phase 10 | Pending |

**Coverage:**
- v1 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-26*
*Last updated: 2026-06-26 after initial definition*
