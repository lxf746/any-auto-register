---
phase: 1
phase_name: Foundation + API v2
plan_id: 1-01
plan_name: Next.js Setup + API v2 Modernization
objective: |
  Set up Next.js 14+ frontend project with TypeScript, Tailwind CSS, Shadcn/ui and modernize
  the backend API with versioning, response envelope, OpenAPI spec, and TypeScript type generation.
requirements: [FE-01, API-01, API-02, API-03, API-04]
wave: 1
files_modified:
  - frontend-new/
  - api/
  - core/
  - main.py
  - package.json
  - tsconfig.json
  - openapi.json
---

# Plan: Next.js Setup + API v2 Modernization

## Objective

Replace the current Vite+React frontend with a Next.js 14+ App Router project using TypeScript, Tailwind CSS, and Shadcn/ui. Simultaneously modernize the backend API with versioned endpoints (/api/v2/), a unified response envelope, auto-generated OpenAPI spec, and TypeScript type generation.

## Tasks

### Task 1: Initialize Next.js Project

Create a new Next.js 14+ project in `frontend-new/` directory:

- `npx create-next-app@latest frontend-new --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"`
- Install dependencies: `shadcn/ui`, `lucide-react`, `class-variance-authority`, `clsx`, `tailwind-merge`
- Configure `tailwind.config.ts` with project theme
- Set up `components.json` for Shadcn/ui CLI
- Add base Shadcn/ui components: button, card, badge, input, label, dialog, dropdown-menu, select, tabs, toast, table
- Configure `next.config.ts` with API proxy to `http://localhost:8000`
- Create `src/lib/api.ts` with typed API client (fetch wrapper with auth headers)
- Create `src/lib/auth.ts` with JWT token management (localStorage)
- Create `src/app/layout.tsx` with root layout, theme provider, toast provider
- Create `src/app/page.tsx` as redirect to `/dashboard`

### Task 2: Create API v2 Router with Response Envelope

Create the v2 API layer in the backend:

- Create `api/v2/` directory with `__init__.py`
- Create `api/v2/router.py` as the v2 API router
- Create `api/v2/response.py` with the unified response envelope:
  ```python
  from pydantic import BaseModel
  from typing import Any, Optional
  
  class ApiResponse(BaseModel):
      ok: bool
      data: Any = None
      error: Optional[str] = None
  ```
- Create `api/v2/deps.py` with shared dependencies (auth, db session)
- Mount v2 router in `main.py` at `/api/v2`
- Migrate auth endpoints to v2:
  - `GET /api/v2/auth/check` → returns `{ok: true, data: {required: bool}}`
  - `POST /api/v2/auth/login` → returns `{ok: true, data: {token: str}}`
- Migrate platforms endpoint to v2:
  - `GET /api/v2/platforms` → returns `{ok: true, data: [...]}`
- Keep v1 endpoints running (backward compatibility during transition)

### Task 3: OpenAPI Spec + TypeScript Generation

Set up automated API contract generation:

- Configure FastAPI's built-in OpenAPI generation at `/api/v2/openapi.json`
- Create `scripts/gen-api-types.sh` script:
  ```bash
  #!/bin/bash
  curl -s http://localhost:8000/api/v2/openapi.json > openapi.json
  npx openapi-typescript openapi.json -o frontend-new/src/lib/api-types.ts
  ```
- Add `openapi-typescript` as dev dependency in `frontend-new/package.json`
- Add npm script: `"gen:api": "bash scripts/gen-api-types.sh"`
- Create `frontend-new/src/lib/api-client.ts` with type-safe API calls using generated types
- Verify generated types work with the API response envelope

### Task 4: Auth Flow Integration

Implement authentication in the new Next.js frontend:

- Create `src/app/(auth)/login/page.tsx` with login form:
  - Password input with validation
  - Submit button with loading state
  - Error display
  - Redirect to `/dashboard` on success
- Create `src/lib/auth-context.tsx` with AuthProvider:
  - Token state management
  - Login/logout functions
  - Auto-check auth on mount (`GET /api/v2/auth/check`)
  - Protected route wrapper
- Create `src/middleware.ts` for route protection:
  - Redirect unauthenticated users to `/login`
  - Allow `/login` and public routes
- Update `src/app/layout.tsx` to wrap with AuthProvider

### Task 5: Dashboard Shell

Create the basic dashboard layout:

- Create `src/app/(dashboard)/layout.tsx` with sidebar navigation:
  - Logo/title
  - Nav items: Dashboard, Accounts, Register, History, Settings
  - Theme toggle (light/dark/system)
  - User menu with logout
- Create `src/app/(dashboard)/dashboard/page.tsx`:
  - Fetch `/api/v2/stats/overview` on mount
  - Display stat cards: total accounts, success rate, active tasks
  - Platform grid (fetch `/api/v2/platforms`)
  - Quick action buttons
- Create `src/components/ui/sidebar.tsx` (Shadcn-style sidebar component)
- Create `src/components/ui/theme-toggle.tsx` for theme switching

## Verification

After execution:
1. `cd frontend-new && npm run dev` starts without errors
2. `http://localhost:3000` redirects to login page
3. Login with correct password redirects to dashboard
4. Dashboard shows platform cards and stats
5. `curl http://localhost:8000/api/v2/openapi.json` returns valid OpenAPI spec
6. `npm run gen:api` produces `api-types.ts` without errors
7. All v1 endpoints still work at `/api/*`
8. All v2 endpoints return `{ok, data, error}` envelope format
