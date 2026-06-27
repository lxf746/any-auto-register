# Roadmap: v2.0 Unified Enterprise Version

**Created:** 2026-06-27
**Milestone Goal:** Удалить v1, v2 становится единственной версией. Один чистый кодбез без дуалов/шимов/компата.
**Phases:** 7
**Requirements:** 28 mapped

## Phases

- [ ] **Phase 1: v1 Removal** - Удалить старый frontend, static, v1 API эндпоинты и все шимы/compat слои
- [ ] **Phase 2: v2 Consolidation** - Перенести auth/accounts из v1 API в v2, оставить только v2 роутер
- [ ] **Phase 3: Account Endpoints** - Реализовать Account CRUD, exports, imports, checks в v2
- [ ] **Phase 4: Core Endpoints** - Реализовать actions, config, health, lifecycle, tasks, system в v2
- [ ] **Phase 5: Provider & Infra Endpoints** - Реализовать providers, proxies, SMS в v2
- [ ] **Phase 6: Stats Endpoints** - Реализовать statistics и monitoring в v2
- [ ] **Phase 7: Cleanup** - Обновить .gitignore, Dockerfile, docker-compose, удалить legacy code

## Phase Details

### Phase 1: v1 Removal
**Goal**: Старый frontend и v1 API полностью удалены, проект не содержит dual-кода
**Depends on**: Nothing (first phase)
**Requirements**: RM-01, RM-02, RM-03, RM-04
**Success Criteria** (what must be TRUE):
  1. Директория frontend/ (Vite+React) отсутствует в проекте
  2. Директория static/ отсутствует в проекте
  3. Файлы api/auth.py, api/accounts.py и другие v1 эндпоинты удалены
  4. Все шимы и compat слои между v1 и v2 удалены — проект не содержит dual-систем
  5. Приложение запускается без ошибок импорта после удаления v1 кода
**Plans**: TBD

Plans:
- [ ] 01-01: Удалить frontend/, static/, v1 API файлы, шимы и compat слои

### Phase 2: v2 Consolidation
**Goal**: Auth functions и AccountsService перенесены в v2, main.py использует только v2 роутер
**Depends on**: Phase 1
**Requirements**: CO-01, CO-02, CO-03, CO-04, CO-05
**Success Criteria** (what must be TRUE):
  1. Auth functions (create_session, validate_session, _check_rate_limit) работают из api/v2/ модуля
  2. AccountsService работает из api/v2/ или shared модуля
  3. main.py подключает только v2 роутер, без v1 роутеров
  4. core/auth.py не содержит v1 public prefixes — авторизация работает только через v2
  5. frontend-new/src/lib/api.ts не содержит v1 response format fallback
**Plans**: TBD

Plans:
- [ ] 02-01: Перенести auth и accounts в v2, обновить main.py, core/auth.py, api.ts

### Phase 3: Account Endpoints
**Goal**: Полный набор Account CRUD, export, import, check эндпоинтов работает в v2
**Depends on**: Phase 2
**Requirements**: EP-01, EP-02, EP-03, EP-04
**Success Criteria** (what must be TRUE):
  1. Account CRUD работает — создание, обновление, удаление, получение по ID
  2. Account exports работают — CSV, JSON, sub2api, cpa, kiro-go, any2api форматы
  3. Account imports работают — загрузка аккаунтов из файлов
  4. Account checks работают — check-all и check-one проверяют статус аккаунтов
**Plans**: TBD

Plans:
- [ ] 03-01: Реализовать Account CRUD эндпоинты
- [ ] 03-02: Реализовать exports, imports, checks

### Phase 4: Core Endpoints
**Goal**: Actions, config, health, lifecycle, tasks и system эндпоинты работают в v2
**Depends on**: Phase 3
**Requirements**: EP-05, EP-06, EP-07, EP-08, EP-15, EP-16
**Success Criteria** (what must be TRUE):
  1. Actions endpoints работают — list, capabilities, execute
  2. Config endpoints работают — get, get options, update
  3. Health/ready/pools/rate-limits endpoint возвращает актуальное состояние
  4. Lifecycle endpoints работают — check, refresh, warn, status
  5. Tasks endpoints работают — list, get, events, logs, register, cancel, stream
  6. System endpoints работают — solver status/restart, version check
**Plans**: TBD

Plans:
- [ ] 04-01: Реализовать actions, config, health, lifecycle
- [ ] 04-02: Реализовать tasks и system endpoints

### Phase 5: Provider & Infra Endpoints
**Goal**: Platform capabilities, provider definitions/settings, proxies и SMS эндпоинты работают в v2
**Depends on**: Phase 4
**Requirements**: EP-09, EP-10, EP-11, EP-12, EP-13
**Success Criteria** (what must be TRUE):
  1. Platform capabilities endpoints работают — update, reset
  2. Provider definitions endpoints работают — CRUD и drivers
  3. Provider settings endpoints работают — CRUD и test
  4. Proxies endpoints работают — CRUD, bulk, toggle, check, scan
  5. SMS endpoints работают — HeroSMS и SmsBower эндпоинты
**Plans**: TBD

Plans:
- [ ] 05-01: Реализовать platform capabilities, providers, proxies, SMS

### Phase 6: Stats Endpoints
**Goal**: Statistics и monitoring эндпоинты работают в v2
**Depends on**: Phase 5
**Requirements**: EP-14
**Success Criteria** (what must be TRUE):
  1. Stats endpoints работают — by-platform, by-day, by-proxy, errors
  2. Статистика возвращается в формате v2 API
**Plans**: TBD

Plans:
- [ ] 06-01: Реализовать stats эндпоинты

### Phase 7: Cleanup
**Goal**: Инфраструктурные файлы обновлены, legacy код удалён, проект готов к production
**Depends on**: Phase 6
**Requirements**: CL-01, CL-02, CL-03, CL-04
**Success Criteria** (what must be TRUE):
  1. .gitignore не содержит frontend/node_modules, frontend/dist
  2. Dockerfile не ссылается на frontend/ директорию
  3. docker-compose.yml не содержит legacy сервисы
  4. Deprecated functions и legacy code удалены из codebase
  5. Проект полностью работает как единая версия без references на v1
**Plans**: TBD

Plans:
- [ ] 07-01: Обновить .gitignore, Dockerfile, docker-compose.yml
- [ ] 07-02: Удалить legacy code и deprecated functions

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. v1 Removal | 0/1 | Not started | - |
| 2. v2 Consolidation | 0/1 | Not started | - |
| 3. Account Endpoints | 0/2 | Not started | - |
| 4. Core Endpoints | 0/2 | Not started | - |
| 5. Provider & Infra Endpoints | 0/1 | Not started | - |
| 6. Stats Endpoints | 0/1 | Not started | - |
| 7. Cleanup | 0/2 | Not started | - |
