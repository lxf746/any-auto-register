---
phase: 2
phase_name: Core UI
plan_id: 2-01
plan_name: Authentication + Dashboard + Task Management + Account List
objective: |
  Build the core UI pages: JWT login/register with form validation, dashboard with platform
  cards and quick actions, task management (create/view/cancel), and account list with search/filter.
requirements: [FE-02, FE-03, FE-04, FE-05]
wave: 1
files_modified:
  - frontend-new/src/app/
  - frontend-new/src/components/
  - frontend-new/src/lib/
---

# Plan: Core UI Pages

## Objective

Build all core user-facing pages: authentication (login/register), dashboard overview, task management, and account listing with search/filter capabilities.

## Tasks

### Task 1: Register Page

Create registration page alongside login:

- Create `src/app/(auth)/register/page.tsx`:
  - Password input with confirmation
  - Submit button with loading state
  - Error/success display
  - Redirect to login on success
- Update auth context to support register flow
- Add register link to login page and vice versa

### Task 2: Dashboard Enhancement

Enhance dashboard with full functionality:

- Update `src/app/(dashboard)/dashboard/page.tsx`:
  - Fetch real stats from `/api/v2/stats/overview`
  - Platform cards showing account counts and success rates
  - Recent activity feed (last 10 registrations)
  - Quick action: "Register Account" button → navigates to /register
  - Quick action: "View Accounts" button → navigates to /accounts
  - Auto-refresh every 30 seconds
- Create `src/components/dashboard/stat-card.tsx` for metric display
- Create `src/components/dashboard/platform-card.tsx` for platform overview
- Create `src/components/dashboard/activity-feed.tsx` for recent registrations

### Task 3: Task Management

Build task creation, viewing, and cancellation:

- Create `src/app/(dashboard)/register/page.tsx`:
  - Platform selector (dropdown from `/api/v2/platforms`)
  - Account count input (1-100)
  - Proxy settings (optional)
  - Captcha solver toggle
  - Submit creates task via `POST /api/v2/tasks/register`
  - Show progress indicator after submission
- Create `src/app/(dashboard)/history/page.tsx`:
  - Task list table with columns: ID, Platform, Status, Created, Duration
  - Status filter (All, Running, Completed, Failed, Cancelled)
  - Date range filter
  - Pagination
  - Click row to view task details
- Create `src/app/(dashboard)/history/[id]/page.tsx`:
  - Task detail view with logs
  - Cancel button (if running)
  - Retry button (if failed)
  - Log stream viewer (SSE from `/api/v2/tasks/{id}/events`)
- Create `src/components/tasks/task-table.tsx` for task listing
- Create `src/components/tasks/task-detail.tsx` for task detail view
- Create `src/components/tasks/log-viewer.tsx` for real-time log streaming

### Task 4: Account List

Build account management with search and filter:

- Create `src/app/(dashboard)/accounts/page.tsx`:
  - Account table with columns: Email, Platform, Status, Created, Last Check
  - Platform filter (dropdown)
  - Status filter (Active, Banned, Unknown)
  - Search by email
  - Pagination
  - Bulk select with actions (Delete, Export)
- Create `src/app/(dashboard)/accounts/[platform]/page.tsx`:
  - Platform-specific account list
  - Platform stats header
  - Bulk operations
- Create `src/components/accounts/account-table.tsx`
- Create `src/components/accounts/account-filters.tsx`
- Create `src/components/accounts/bulk-actions.tsx`

### Task 5: Shared Components

Create reusable components:

- Create `src/components/ui/data-table.tsx` — generic table with sorting, pagination
- Create `src/components/ui/search-input.tsx` — debounced search input
- Create `src/components/ui/filter-select.tsx` — dropdown filter component
- Create `src/components/ui/loading-spinner.tsx` — loading indicator
- Create `src/components/ui/empty-state.tsx` — empty state placeholder
- Create `src/components/ui/error-boundary.tsx` — error boundary wrapper
- Create `src/hooks/use-api.ts` — custom hook for API calls with loading/error states
- Create `src/hooks/use-debounce.ts` — debounce hook for search

## Verification

After execution:
1. `/login` page renders with form validation
2. `/register` page renders with password confirmation
3. Login/Register flow works end-to-end
4. Dashboard shows real data from API
5. `/register` page creates tasks successfully
6. `/history` page lists tasks with filters
7. `/accounts` page lists accounts with search
8. All pages are responsive (mobile-friendly)
9. Dark/light theme works across all pages
