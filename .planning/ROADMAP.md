# Roadmap: Security Hardening

**Milestone:** v1.0 Security Hardening
**Created:** 2026-06-26

## Phase Overview

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|------------------|
| 1 | Critical Auth Fixes | Исправить критические уязвимости аутентификации | AUTH-01, AUTH-02 | 2 |
| 2 | Secrets & Data Protection | Защита секретов и данных в БД | AUTH-03, AUTH-04, DATA-01, VALD-01 | 4 |
| 3 | Network Security | Сетевая безопасность и rate limiting | AUTH-05, DATA-02, DATA-03 | 3 |

**Total: 3 phases | 9 requirements | All covered ✓**

## Phase Details

### Phase 1: Critical Auth Fixes

**Goal:** Исправить критические уязвимости в механизме аутентификации

**Requirements:**
- AUTH-01: Password comparison uses timing-safe comparison
- AUTH-02: Auth middleware generates random session tokens

**Success criteria:**
1. `api/auth.py` использует `hmac.compare_digest()` для сравнения паролей
2. Auth middleware возвращает случайный токен вместо пароля, пароль хешируется при сохранении

**Files to modify:**
- `api/auth.py` — timing-safe comparison + token generation
- `core/auth.py` — token verification logic

---

### Phase 2: Secrets & Data Protection

**Goal:** Принудительная конфигурация секретов и защита паролей в БД

**Requirements:**
- AUTH-03: JWT secret must be explicitly configured
- AUTH-04: Admin credentials must be explicitly configured
- DATA-01: Passwords encrypted at rest in SQLite
- VALD-01: SQL injection prevention in _ensure_column

**Success criteria:**
1. `customer_portal_api/app/config.py` проверяет что `PORTAL_JWT_SECRET` установлен и не является дефолтным
2. `customer_portal_api/app/config.py` проверяет что admin creds заданы через env vars
3. Пароли шифруются при записи в БД и расшифровываются при чтении
4. `_ensure_column` валидирует имена таблиц/колонок через allowlist

**Files to modify:**
- `customer_portal_api/app/config.py` — secrets validation
- `core/db.py` — password encryption + SQL injection prevention

---

### Phase 3: Network Security

**Goal:** Ограничение сети и предотвращение brute-force

**Requirements:**
- AUTH-05: Rate limiting on auth endpoints
- DATA-02: TLS verification enabled by default
- DATA-03: CORS restricted to specific origins

**Success criteria:**
1. Rate limiting middleware на `/api/auth/login` (slowapi или аналог)
2. `core/tls.py` — TLS verification включена по умолчанию, `insecure_request()` требует явного флага
3. CORS `allow_origins` настроен на конкретные домены вместо `*`

**Files to modify:**
- `api/auth.py` — rate limiting middleware
- `core/tls.py` — TLS verification default
- `main.py` — CORS origins
- `customer_portal_api/main.py` — CORS origins

---
*Created: 2026-06-26*
