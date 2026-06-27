---
phase: 02-v2-consolidation
plan: 01
type: execute
wave: 1
depends_on: [01-02]
files_modified: [core/auth.py, frontend-new/src/lib/api.ts]
autonomous: true
requirements: [CO-01, CO-02, CO-03, CO-04, CO-05]

must_haves:
  truths:
    - "Auth functions (create_session, validate_session, _check_rate_limit) work from api/v2/auth.py"
    - "AccountsService works from api/v2/router.py with no v1 imports"
    - "main.py connects only v2 router, no v1 routers"
    - "core/auth.py has no v1 public prefixes — auth works only through v2"
    - "frontend API client has no v1 response format fallback"
  artifacts:
    - "core/auth.py"
    - "frontend-new/src/lib/api.ts"
  key_links:
    - "core/auth.py → api/v2/auth.py (validate_session import)"
    - "api/v2/router.py → application/accounts.py (AccountsService import)"
---

<objective>
Clean up remaining v1 artifacts in core/auth.py and frontend-new/src/lib/api.ts.

Purpose: Phase 1 already migrated auth functions to api/v2/auth.py and removed v1 API files. This plan removes the last v1 references: the `/api/auth/` public prefix in core/auth.py and the v1 response format fallback in api.ts.

Output: core/auth.py with only v2 public prefixes; api.ts with only v2 envelope handling.
</objective>

<execution_context>
@gsd-core/workflows/execute-plan.md
@gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/01-v1-removal/01-02-SUMMARY.md
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Remove v1 public prefix from core/auth.py</name>
  <files>core/auth.py</files>
  <behavior>
    - Test: _PUBLIC_PREFIXES contains only "/api/health", "/api/ready", "/api/v2/auth/"
    - Test: "/api/auth/some-path" is NOT in _PUBLIC_PREFIXES (v1 prefix removed)
    - Test: "/api/v2/auth/check" IS in _PUBLIC_PREFIXES (v2 preserved)
  </behavior>
  <action>
Edit core/auth.py line 22. Change _PUBLIC_PREFIXES from:
  ("/api/health", "/api/ready", "/api/auth/", "/api/v2/auth/")
to:
  ("/api/health", "/api/ready", "/api/v2/auth/")

This removes the v1 auth prefix. The `/api/auth/` prefix is a remnant of the old v1 API that no longer exists. Per CO-04, core/auth.py must not contain v1 public prefixes.

Do NOT remove "/api/health" or "/api/ready" — those are infrastructure endpoints, not v1.
Do NOT remove "/api/v2/auth/" — that's the current auth prefix.
  </action>
  <verify>
    <automated>cd /home/vitaly/projects/any-auto-register && python3 -c "from core.auth import _PUBLIC_PREFIXES; assert '/api/auth/' not in _PUBLIC_PREFIXES, 'v1 prefix still present'; assert '/api/v2/auth/' in _PUBLIC_PREFIXES, 'v2 prefix missing'; print('OK: public prefixes correct')"</automated>
  </verify>
  <done>_PUBLIC_PREFIXES no longer contains "/api/auth/" (v1). v2 and infrastructure prefixes preserved.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Remove v1 response format fallback from api.ts</name>
  <files>frontend-new/src/lib/api.ts</files>
  <behavior>
    - Test: api.ts request function throws ApiError when json.ok is false
    - Test: api.ts request function returns json.data when json.ok is true
    - Test: api.ts does NOT have a fallback that returns raw json without envelope check
  </behavior>
  <action>
Edit frontend-new/src/lib/api.ts. Remove lines 57-58 (the v1 fallback block):
  // Handle v1 format: return raw response
  return json as T;

After removal, the request function should only handle the v2 envelope format. If the response does not have the v2 envelope ({ ok, data }), throw an error — this indicates the backend is not returning v2 format, which should never happen after Phase 2 consolidation.

Per CO-05, the frontend API client must not contain v1 response format fallback.
  </action>
  <verify>
    <automated>cd /home/vitaly/projects/any-auto-register && grep -c "v1 format" frontend-new/src/lib/api.ts | grep -q "^0$" && echo "OK: v1 fallback removed" || echo "FAIL: v1 fallback still present"</automated>
  </verify>
  <done>frontend-new/src/lib/api.ts does not contain "v1 format" fallback. Only v2 envelope handling remains.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| client→API | Unauthenticated requests must be rejected when APP_PASSWORD is set |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-02-01 | Tampering | core/auth.py _PUBLIC_PREFIXES | medium | mitigate | Removing v1 prefix prevents unauthorized access to non-existent v1 endpoints |
| T-02-02 | Information Disclosure | api.ts v1 fallback | low | mitigate | Removing fallback ensures all responses are validated via v2 envelope |
</threat_model>

<verification>
- `python3 -c "from main import app"` — app starts without import errors
- `python3 -c "from core.auth import _PUBLIC_PREFIXES; assert '/api/auth/' not in _PUBLIC_PREFIXES"` — v1 prefix removed
- `grep -c "v1 format" frontend-new/src/lib/api.ts` returns 0 — no v1 fallback
</verification>

<success_criteria>
All five success criteria from ROADMAP.md are met:
1. Auth functions work from api/v2/auth.py (already done in Phase 1)
2. AccountsService works from api/v2/router.py (already done in Phase 1)
3. main.py uses only v2 router (already done in Phase 1)
4. core/auth.py has no v1 public prefixes
5. frontend API client has no v1 response format fallback
</success_criteria>

<output>
Create `.planning/phases/02-v2-consolidation/02-01-SUMMARY.md` when done
</output>
