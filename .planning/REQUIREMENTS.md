# Requirements: Any Auto Register

**Defined:** 2026-06-27
**Core Value:** Автоматическая регистрация аккаунтов должна работать надёжно и безопасно

## v2.0 Requirements

### v1 Removal

- [x] **RM-01**: Удалить frontend/ (Vite+React) — заменён на frontend-new/
- [x] **RM-02**: Удалить static/ — build output старого фронтенда
- [x] **RM-03**: Удалить v1 API эндпоинты (api/auth.py, api/accounts.py, и т.д.)
- [x] **RM-04**: Удалить все шимы и compat слои между v1 и v2

### v2 Consolidation

- [x] **CO-01**: Перенести auth functions (create_session, validate_session, _check_rate_limit, _sessions) из api/auth.py в api/v2/
- [x] **CO-02**: Перенести AccountsService из api/accounts.py в api/v2/ или shared module
- [x] **CO-03**: Обновить main.py — оставить только v2 роутер
- [x] **CO-04**: Обновить core/auth.py — убрать v1 public prefixes
- [x] **CO-05**: Обновить frontend-new/src/lib/api.ts — убрать v1 response format fallback

### Missing v2 Endpoints

- [x] **EP-01**: Account CRUD (create, update, delete, get by ID)
- [x] **EP-02**: Account exports (CSV, JSON, sub2api, cpa, kiro-go, any2api)
- [x] **EP-03**: Account imports
- [x] **EP-04**: Account checks (check-all, check-one)
- [x] **EP-05**: Actions (list, capabilities, execute)
- [x] **EP-06**: Config (get, get options, update)
- [x] **EP-07**: Health/ready/pools/rate-limits
- [ ] **EP-08**: Lifecycle (check, refresh, warn, status)
- [ ] **EP-09**: Platform capabilities (update, reset)
- [ ] **EP-10**: Provider definitions (CRUD, drivers)
- [ ] **EP-11**: Provider settings (CRUD, test)
- [ ] **EP-12**: Proxies (CRUD, bulk, toggle, check, scan)
- [ ] **EP-13**: SMS (HeroSMS, SmsBower endpoints)
- [ ] **EP-14**: Stats (by-platform, by-day, by-proxy, errors)
- [ ] **EP-15**: Tasks (list, get, events, logs, register, cancel, stream)
- [ ] **EP-16**: System (solver status/restart, version check)

### Cleanup

- [ ] **CL-01**: Обновить .gitignore — убрать frontend/node_modules, frontend/dist
- [ ] **CL-02**: Обновить Dockerfile — убрать reference на frontend/
- [ ] **CL-03**: Обновить docker-compose.yml если нужно
- [ ] **CL-04**: Удалить legacy code и deprecated functions

## v3 Requirements

### Advanced Features

- **ADV-01**: Multi-user support with role-based access control
- **ADV-02**: Webhook notifications for task completion
- **ADV-03**: API key management for external integrations
- **ADV-04**: Batch operations — bulk register/cancel accounts

## Out of Scope

| Feature | Reason |
|---------|--------|
| Mobile app | Web-first, responsive design covers mobile |
| Real-time chat | Not core to registration workflow |
| Video tutorials | Documentation covers onboarding |
| Kubernetes deployment | Infrastructure, not application |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| RM-01 | Phase 1: v1 Removal | Complete |
| RM-02 | Phase 1: v1 Removal | Complete |
| RM-03 | Phase 1: v1 Removal | Complete |
| RM-04 | Phase 1: v1 Removal | Complete |
| CO-01 | Phase 2: v2 Consolidation | Complete |
| CO-02 | Phase 2: v2 Consolidation | Complete |
| CO-03 | Phase 2: v2 Consolidation | Complete |
| CO-04 | Phase 2: v2 Consolidation | Complete |
| CO-05 | Phase 2: v2 Consolidation | Complete |
| EP-01 | Phase 3: Account Endpoints | Complete |
| EP-02 | Phase 3: Account Endpoints | Complete |
| EP-03 | Phase 3: Account Endpoints | Complete |
| EP-04 | Phase 3: Account Endpoints | Complete |
| EP-05 | Phase 4: Core Endpoints | Complete |
| EP-06 | Phase 4: Core Endpoints | Complete |
| EP-07 | Phase 4: Core Endpoints | Complete |
| EP-08 | Phase 4: Core Endpoints | Pending |
| EP-15 | Phase 4: Core Endpoints | Pending |
| EP-16 | Phase 4: Core Endpoints | Pending |
| EP-09 | Phase 5: Provider & Infra Endpoints | Pending |
| EP-10 | Phase 5: Provider & Infra Endpoints | Pending |
| EP-11 | Phase 5: Provider & Infra Endpoints | Pending |
| EP-12 | Phase 5: Provider & Infra Endpoints | Pending |
| EP-13 | Phase 5: Provider & Infra Endpoints | Pending |
| EP-14 | Phase 6: Stats Endpoints | Pending |
| CL-01 | Phase 7: Cleanup | Pending |
| CL-02 | Phase 7: Cleanup | Pending |
| CL-03 | Phase 7: Cleanup | Pending |
| CL-04 | Phase 7: Cleanup | Pending |

**Coverage:**
- v2.0 requirements: 28 total
- Mapped to phases: 28/28 ✓
- Unmapped: 0 ✓
- Phase 1 (v1 Removal): 4 requirements
- Phase 2 (v2 Consolidation): 5 requirements
- Phase 3 (Account Endpoints): 4 requirements
- Phase 4 (Core Endpoints): 6 requirements
- Phase 5 (Provider & Infra Endpoints): 5 requirements
- Phase 6 (Stats Endpoints): 1 requirement
- Phase 7 (Cleanup): 4 requirements

---
*Requirements defined: 2026-06-27*
*Last updated: 2026-06-27 after initial definition*
