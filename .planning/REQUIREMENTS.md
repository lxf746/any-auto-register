# Requirements: Security Hardening

**Defined:** 2026-06-26
**Core Value:** Аккаунты и данные должны быть защищены от компрометации

## v1 Requirements

### Auth Security

- [ ] **AUTH-01**: Password comparison uses timing-safe comparison (hmac.compare_digest) instead of ==
- [ ] **AUTH-02**: Auth middleware generates random session tokens instead of returning password as token
- [ ] **AUTH-03**: JWT secret must be explicitly configured — startup fails if default value detected
- [ ] **AUTH-04**: Admin credentials must be explicitly configured — startup fails if default values detected
- [ ] **AUTH-05**: Rate limiting on auth endpoints to prevent brute-force

### Data Protection

- [ ] **DATA-01**: Passwords encrypted at rest in SQLite database
- [ ] **DATA-02**: TLS verification enabled by default, opt-in only for insecure connections
- [ ] **DATA-03**: CORS restricted to specific origins instead of wildcard

### Input Validation

- [ ] **VALD-01**: SQL injection prevention in _ensure_column — validate table/column names

## v2 Requirements

Deferred to future milestone.

### Auth Security

- **AUTH-06**: OAuth2/JWT refresh token rotation
- **AUTH-07**: Session expiration and token invalidation

### Data Protection

- **DATA-04**: Database encryption at rest (SQLite encryption or migration to PostgreSQL)
- **DATA-05**: Secrets management via environment variables or vault

## Out of Scope

| Feature | Reason |
|---------|--------|
| Refactoring monolithic files | Separate milestone — security first |
| Adding test coverage | Separate milestone — fix vulnerabilities first |
| PostgreSQL migration | Separate milestone — different scope |
| Rate limiting beyond auth | Lower priority, address in v2 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | Phase 1 | Pending |
| AUTH-02 | Phase 1 | Pending |
| AUTH-03 | Phase 2 | Pending |
| AUTH-04 | Phase 2 | Pending |
| AUTH-05 | Phase 3 | Pending |
| DATA-01 | Phase 2 | Pending |
| DATA-02 | Phase 3 | Pending |
| DATA-03 | Phase 3 | Pending |
| VALD-01 | Phase 2 | Pending |

**Coverage:**
- v1 requirements: 9 total
- Mapped to phases: 9
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-26*
*Last updated: 2026-06-26 after initial definition*
