---
phase: 3
phase_name: Analytics Dashboard
plan_id: 3-01
plan_name: Stats, Charts, Metrics, Export
objective: |
  Build analytics dashboard with registration stats (success/failure rates, timeline charts),
  platform breakdown, performance metrics, and data export (CSV/JSON).
requirements: [AN-01, AN-02, AN-03, AN-04]
wave: 1
files_modified:
  - frontend-new/src/app/(dashboard)/analytics/
  - frontend-new/src/components/analytics/
  - api/v2/stats.py
---

# Plan: Analytics Dashboard

## Objective

Create a comprehensive analytics dashboard with interactive charts showing registration statistics, platform breakdown, performance metrics, and data export capabilities.

## Tasks

### Task 1: Analytics Page Layout

Create the analytics page structure:

- Create `src/app/(dashboard)/analytics/page.tsx`:
  - Date range picker (Last 7 days, 30 days, 90 days, Custom)
  - Stats overview cards (total registrations, success rate, avg time)
  - Tab navigation: Overview, Platforms, Performance, Export
- Create `src/components/analytics/date-range-picker.tsx`
- Create `src/components/analytics/stats-overview.tsx`
- Add analytics route to sidebar navigation

### Task 2: Registration Stats Charts

Build registration statistics visualizations:

- Install `recharts` as dependency
- Create `src/components/analytics/registration-chart.tsx`:
  - Area chart showing registrations over time
  - Stacked by status (success/failed/cancelled)
  - Tooltip with detailed numbers
  - Responsive sizing
- Create `src/components/analytics/success-rate-chart.tsx`:
  - Line chart showing success rate % over time
  - Reference line at 90% target
  - Color coding: green (>90%), yellow (70-90%), red (<70%)
- Fetch data from `GET /api/v2/stats/by-day`

### Task 3: Platform Breakdown

Build per-platform analytics:

- Create `src/components/analytics/platform-breakdown.tsx`:
  - Bar chart comparing platforms by registration count
  - Pie chart for market share
  - Table with detailed per-platform metrics
- Create `src/components/analytics/platform-card-detail.tsx`:
  - Platform name and icon
  - Success rate gauge
  - Total accounts
  - Avg registration time
  - Error count
- Fetch data from `GET /api/v2/stats/by-platform`

### Task 4: Performance Metrics

Build performance monitoring views:

- Create `src/components/analytics/performance-metrics.tsx`:
  - Avg registration time by platform
  - Error rate over time
  - Response time distribution
- Create `src/components/analytics/error-breakdown.tsx`:
  - Top errors by frequency
  - Error trend over time
  - Error by platform
- Fetch data from `GET /api/v2/stats/errors`

### Task 5: Data Export

Implement export functionality:

- Create `src/components/analytics/export-panel.tsx`:
  - Export format selector (CSV, JSON)
  - Date range filter
  - Platform filter
  - Export button with download
- Create `src/lib/export.ts`:
  - `exportCSV(data, filename)` — convert to CSV and download
  - `exportJSON(data, filename)` — format and download
  - `fetchExportData(filters)` — fetch from API
- Add export endpoints if needed:
  - `POST /api/v2/stats/export` with format and filters

### Task 6: Backend Stats Endpoints

Ensure backend has all needed stats endpoints:

- Verify `GET /api/v2/stats/overview` returns:
  ```json
  {"ok": true, "data": {"total": N, "success_rate": float, "avg_time": float}}
  ```
- Verify `GET /api/v2/stats/by-day` returns daily breakdown
- Verify `GET /api/v2/stats/by-platform` returns per-platform stats
- Verify `GET /api/v2/stats/errors` returns error breakdown
- Add any missing endpoints to `api/v2/stats.py`

## Verification

After execution:
1. `/analytics` page loads without errors
2. Date range picker filters data correctly
3. Registration chart shows real data
4. Platform breakdown shows all platforms
5. Performance metrics display correctly
6. Export downloads CSV/JSON with correct data
7. Charts are responsive and interactive
8. Dark/light theme works on all charts
