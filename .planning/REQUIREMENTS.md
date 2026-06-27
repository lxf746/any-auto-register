# Requirements: Any Auto Register

**Defined:** 2026-06-27
**Core Value:** Автоматическая регистрация аккаунтов должна работать надёжно и безопасно

## v1.7 Requirements

### Frontend Core

- [ ] **FE-01**: Next.js 14+ project setup with TypeScript, Tailwind CSS, Shadcn/ui
- [ ] **FE-02**: Authentication — JWT login/register pages with form validation
- [ ] **FE-03**: Dashboard — main overview page with platform cards and quick actions
- [ ] **FE-04**: Task Management — create, view, cancel registration tasks
- [ ] **FE-05**: Account List — view all registered accounts with search/filter

### Analytics Dashboard

- [ ] **AN-01**: Registration stats — success/failure rates, timeline charts
- [ ] **AN-02**: Platform breakdown — per-platform registration metrics
- [ ] **AN-03**: Performance metrics — avg registration time, error rates
- [ ] **AN-04**: Export — download stats as CSV/JSON

### Real-time Updates

- [ ] **RT-01**: WebSocket connection — establish WS for live task updates
- [ ] **RT-02**: Task status streaming — real-time progress without polling
- [ ] **RT-03**: Connection management — reconnect on disconnect, heartbeat

### Settings Management

- [ ] **SM-01**: Mailbox providers — enable/disable/configure providers
- [ ] **SM-02**: SMS providers — manage SMS verification providers
- [ ] **SM-03**: Captcha providers — configure captcha solving services
- [ ] **SM-04**: Proxy settings — manage proxy list and rotation
- [ ] **SM-05**: Platform config — per-platform rate limits and settings

### Logs & Debug

- [ ] **LD-01**: Task logs — view detailed logs per registration task
- [ ] **LD-02**: Error viewer — filter and search errors with stack traces
- [ ] **LD-03**: Debug mode — step-by-step registration flow visualization

### Backend API v2

- [ ] **API-01**: API versioning — /api/v2/ prefix for new endpoints
- [ ] **API-02**: Response envelope —统一 {ok, data, error} format
- [ ] **API-03**: OpenAPI spec — auto-generated from FastAPI routes
- [ ] **API-04**: TypeScript gen — openapi-typescript for type-safe API calls
- [ ] **API-05**: WebSocket endpoint — /api/v2/ws for real-time updates

## v2 Requirements

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
| FE-01 | Phase 1 | Pending |
| FE-02 | Phase 1 | Pending |
| FE-03 | Phase 2 | Pending |
| FE-04 | Phase 2 | Pending |
| FE-05 | Phase 2 | Pending |
| AN-01 | Phase 3 | Pending |
| AN-02 | Phase 3 | Pending |
| AN-03 | Phase 3 | Pending |
| AN-04 | Phase 3 | Pending |
| RT-01 | Phase 4 | Pending |
| RT-02 | Phase 4 | Pending |
| RT-03 | Phase 4 | Pending |
| SM-01 | Phase 5 | Pending |
| SM-02 | Phase 5 | Pending |
| SM-03 | Phase 5 | Pending |
| SM-04 | Phase 5 | Pending |
| SM-05 | Phase 5 | Pending |
| LD-01 | Phase 6 | Pending |
| LD-02 | Phase 6 | Pending |
| LD-03 | Phase 6 | Pending |
| API-01 | Phase 1 | Pending |
| API-02 | Phase 1 | Pending |
| API-03 | Phase 1 | Pending |
| API-04 | Phase 1 | Pending |
| API-05 | Phase 4 | Pending |

**Coverage:**
- v1.7 requirements: 25 total
- Mapped to phases: 25
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-27*
*Last updated: 2026-06-27 after initial definition*
