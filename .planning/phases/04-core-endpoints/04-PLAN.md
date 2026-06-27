---
phase: 04-core-endpoints
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - api/v2/health.py
  - api/v2/config.py
  - api/v2/actions.py
  - api/v2/router.py
autonomous: true
requirements: [EP-05, EP-06, EP-07]

must_haves:
  truths:
    - GET /api/v2/health returns {"ok": true, "service": "account-manager-v2"}
    - GET /api/v2/health/ready returns readiness status with database, registry, solver checks
    - GET /api/v2/health/pools returns database, HTTP, and browser pool metrics
    - GET /api/v2/health/rate-limits returns rate limit metrics
    - GET /api/v2/config returns filtered config key-value pairs
    - GET /api/v2/config/options returns platform choices, provider definitions, and settings
    - PUT /api/v2/config updates allowed config keys
    - GET /api/v2/actions/{platform} lists available actions for a platform
    - GET /api/v2/actions/{platform}/capabilities lists capabilities for a platform
    - POST /api/v2/actions/{platform}/execute executes an action (sync or async task)
  artifacts:
    - api/v2/health.py
    - api/v2/config.py
    - api/v2/actions.py
  key_links:
    - api/v2/router.py includes all three new routers
    - Endpoints use ApiResponse envelope consistently
    - All application services are already implemented in application/
---

<objective>
Create v2 API endpoints for Health, Config, and Actions by wrapping existing application services.

Purpose: Expose health monitoring, configuration management, and platform action execution through the v2 API.
Output: Three new endpoint files registered in the v2 router, following the established ApiResponse pattern.
</objective>

<execution_context>
@/home/vitaly/.config/opencode/gsd-core/workflows/execute-plan.md
@/home/vitaly/.config/opencode/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@api/v2/accounts.py
@api/v2/router.py
@api/v2/response.py
@application/health.py
@application/config.py
@application/actions.py
@infrastructure/health_runtime.py
@infrastructure/system_runtime.py
@infrastructure/config_repository.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create health endpoints (api/v2/health.py)</name>
  <files>api/v2/health.py</files>
  <action>
Create `api/v2/health.py` with an `APIRouter(prefix="/health", tags=["health"])`.

Import `HealthService` from `application.health` and `ApiResponse` from `api.v2.response`.

Instantiate service: `_service = HealthService()`

Create four GET endpoints:

1. `GET /` — calls `_service.health()`, returns `ApiResponse(ok=True, data=result)`
2. `GET /ready` — calls `_service.readiness()`, returns `ApiResponse(ok=True, data=result)`
3. `GET /pools` — calls `_service.pool_status()`, returns `ApiResponse(ok=True, data=result)`
4. `GET /rate-limits` — calls `_service.rate_limit_status()`, returns `ApiResponse(ok=True, data=result)`

Follow the exact pattern from `api/v2/accounts.py`: module docstring, imports, router instantiation, service instantiation, endpoint functions with ApiResponse envelope. No request bodies needed — all are simple GET endpoints.
  </action>
  <verify>
    <automated>python -c "from api.v2.health import router; print('health router ok, routes:', [r.path for r in router.routes])"</automated>
  </verify>
  <done>api/v2/health.py exists with 4 GET endpoints returning ApiResponse envelopes. Health service is properly imported and called.</done>
</task>

<task type="auto">
  <name>Task 2: Create config and actions endpoints</name>
  <files>api/v2/config.py, api/v2/actions.py</files>
  <action>
Create `api/v2/config.py` with an `APIRouter(prefix="/config", tags=["config"])`.

Import `ConfigService` from `application.config` and `ApiResponse` from `api.v2.response`.
Instantiate: `_service = ConfigService()`

Create three endpoints:

1. `GET /` — calls `_service.get_config()`, returns `ApiResponse(ok=True, data=result)`
2. `GET /options` — calls `_service.get_options()`, returns `ApiResponse(ok=True, data=result)`
3. `PUT /` — accepts `body: dict[str, str]` (use `Request` from FastAPI and read body, or define a simple Pydantic model `ConfigUpdateRequest` with `data: dict[str, str]`), calls `_service.update_config(body.data)`, returns `ApiResponse(ok=True, data=result)`

---

Create `api/v2/actions.py` with an `APIRouter(prefix="/actions", tags=["actions"])`.

Import `ActionsService` from `application.actions`, `ActionExecutionCommand` from `domain.actions`, and `ApiResponse` from `api.v2.response`.
Instantiate: `_service = ActionsService()`

Define request model:
```python
class ActionExecuteRequest(BaseModel):
    account_id: int
    action_id: str
    params: dict = {}
```

Create three endpoints:

1. `GET /{platform}` — calls `_service.list_actions(platform)`, returns `ApiResponse(ok=True, data=result)`
2. `GET /{platform}/capabilities` — calls `_service.list_capabilities(platform)`, returns `ApiResponse(ok=True, data=result)`
3. `POST /{platform}/execute` — reads body into `ActionExecuteRequest`, builds `ActionExecutionCommand(platform=platform, account_id=body.account_id, action_id=body.action_id, params=body.params)`, calls `_service.execute_action(command)`, returns `ApiResponse(ok=True, data=result)`

Follow the same file structure pattern as `api/v2/accounts.py`.
  </action>
  <verify>
    <automated>python -c "from api.v2.config import router; print('config router ok:', [r.path for r in router.routes]); from api.v2.actions import router; print('actions router ok:', [r.path for r in router.routes])"</automated>
  </verify>
  <done>api/v2/config.py exists with GET /, GET /options, PUT /. api/v2/actions.py exists with GET /{platform}, GET /{platform}/capabilities, POST /{platform}/execute. All use ApiResponse envelope.</done>
</task>

<task type="auto">
  <name>Task 3: Register routers and verify full stack</name>
  <files>api/v2/router.py</files>
  <action>
Update `api/v2/router.py` to import and include the three new routers:

At the top, add imports:
```python
from api.v2.health import router as health_router
from api.v2.config import router as config_router
from api.v2.actions import router as actions_router
```

After the existing `router.include_router(accounts_router)` line, add:
```python
router.include_router(health_router)
router.include_router(config_router)
router.include_router(actions_router)
```

Then verify by importing the main app and checking all routes are registered. Run:
```bash
python -c "from main import app; routes = [r.path for r in app.routes if hasattr(r, 'path')]; print('Total routes:', len(routes)); [print(r) for r in sorted(routes) if '/api/v2/' in r]"
```

Verify that health, config, and actions routes all appear in the output with `/api/v2/` prefix.
  </action>
  <verify>
    <automated>python -c "
from main import app
routes = [r.path for r in app.routes if hasattr(r, 'path')]
v2_routes = [r for r in sorted(routes) if '/api/v2/' in r]
assert any('/health' in r for r in v2_routes), 'health routes missing'
assert any('/config' in r for r in v2_routes), 'config routes missing'
assert any('/actions' in r for r in v2_routes), 'actions routes missing'
print(f'All v2 core endpoint routes registered: {len(v2_routes)} routes')
for r in v2_routes: print(f'  {r}')
"</automated>
  </verify>
  <done>All three routers registered in api/v2/router.py. App imports cleanly. Health, config, and actions routes appear under /api/v2/ prefix.</done>
</task>

</tasks>

<verification>
After all three tasks complete:

1. Start the app and verify health endpoints respond:
```bash
python -c "from main import app; import uvicorn; uvicorn.run(app, host='0.0.0.0', port=8000)" &
sleep 3
curl -s http://localhost:8000/api/v2/health | python -m json.tool
curl -s http://localhost:8000/api/v2/health/ready | python -m json.tool
curl -s http://localhost:8000/api/v2/config | python -m json.tool
curl -s http://localhost:8000/api/v2/config/options | python -m json.tool
kill %1
```

2. All responses use `{"ok": true, "data": {...}}` envelope format.
3. No import errors on `python -c "from main import app"`.
</verification>

<success_criteria>
- api/v2/health.py created with 4 GET endpoints (/health, /ready, /pools, /rate-limits)
- api/v2/config.py created with 3 endpoints (GET /, GET /options, PUT /)
- api/v2/actions.py created with 3 endpoints (GET /{platform}, GET /{platform}/capabilities, POST /{platform}/execute)
- api/v2/router.py updated to include all three routers
- App imports without errors
- All endpoints return ApiResponse envelope
- Requirements EP-05, EP-06, EP-07 satisfied
</success_criteria>

<output>
Create `.planning/phases/04-core-endpoints/04-01-SUMMARY.md` when done
</output>
