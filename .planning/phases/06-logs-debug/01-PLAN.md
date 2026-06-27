---
phase: 6
phase_name: Logs & Debug
plan_id: 6-01
plan_name: Task Logs, Error Viewer, Debug Mode
objective: |
  Build logging and debugging UI: detailed task logs, error viewer with filtering and search,
  and debug mode for step-by-step registration flow visualization.
requirements: [LD-01, LD-02, LD-03]
wave: 1
files_modified:
  - frontend-new/src/app/(dashboard)/logs/
  - frontend-new/src/components/logs/
  - frontend-new/src/lib/debug.ts
---

# Plan: Logs & Debug UI

## Objective

Create comprehensive logging and debugging interfaces for viewing task logs, analyzing errors, and visualizing registration flows step-by-step.

## Tasks

### Task 1: Task Logs Page

Build dedicated logs viewing page:

- Create `src/app/(dashboard)/logs/page.tsx`:
  - Task selector dropdown (fetch from `/api/v2/tasks`)
  - Log level filter (DEBUG, INFO, WARNING, ERROR)
  - Timestamp display
  - Search within logs
  - Auto-scroll toggle
  - Export logs button
- Create `src/components/logs/log-viewer.tsx`:
  - Virtualized log list (for performance with large logs)
  - Syntax highlighting for structured logs
  - Expandable log details
  - Copy log entry button
  - Filter by log source (browser, server, provider)
- Create `src/components/logs/log-filters.tsx`:
  - Level filter (multi-select)
  - Source filter
  - Time range filter
  - Text search

### Task 2: Error Viewer

Build error analysis interface:

- Create `src/app/(dashboard)/logs/errors/page.tsx`:
  - Error list with grouping by message
  - Frequency count per error
  - Last occurrence timestamp
  - Affected platforms
- Create `src/components/logs/error-list.tsx`:
  - Error message with count badge
  - Platform tags
  - First/last seen timestamps
  - Expand to see stack trace
  - Click to see all occurrences
- Create `src/components/logs/error-detail.tsx`:
  - Full stack trace with syntax highlighting
  - Request/response context
  - Environment info
  - Related logs
  - Similar errors list
- Create `src/components/logs/error-stats.tsx`:
  - Error rate chart (over time)
  - Top errors by frequency
  - Errors by platform pie chart
- Fetch from `GET /api/v2/stats/errors`

### Task 3: Debug Mode

Build registration flow visualization:

- Create `src/app/(dashboard)/logs/debug/page.tsx`:
  - Task selector for debugging
  - Step-by-step flow visualization
  - Timeline view
  - State inspector
- Create `src/components/debug/flow-visualizer.tsx`:
  - Vertical timeline with steps
  - Each step shows:
    - Step name (Navigate, Fill Form, Click, etc.)
    - Duration
    - Status (success/fail/pending)
    - Screenshot (if available)
    - Action details
  - Click step to expand details
- Create `src/components/debug/state-inspector.tsx`:
  - Current browser state
  - DOM snapshot
  - Network requests
  - Cookies
  - Local storage
- Create `src/components/debug/network-log.tsx`:
  - HTTP request/response pairs
  - Headers viewer
  - Body viewer (formatted JSON)
  - Timing waterfall

### Task 4: Real-time Log Streaming

Integrate WebSocket for live logs:

- Create `src/hooks/use-live-logs.ts`:
  - Subscribe to task log topic via WebSocket
  - Append new entries in real-time
  - Buffer for performance
  - Pause/resume
- Update `src/components/logs/log-viewer.tsx`:
  - Support both historical and live modes
  - Live indicator when streaming
  - Pause button
  - Buffer size indicator
- Update `src/app/(dashboard)/logs/page.tsx`:
  - Live mode toggle
  - Task selector for live streaming

### Task 5: Log Export and Analysis

Add export and analysis features:

- Create `src/components/logs/log-export.tsx`:
  - Export format: plain text, JSON, CSV
  - Date range filter
  - Level filter
  - Download button
- Create `src/components/logs/log-analysis.tsx`:
  - Average response times
  - Error rate trends
  - Slowest operations
  - Most active platforms
- Create `src/lib/log-utils.ts`:
  - `parseLogEntry(raw)` — structured log parser
  - `formatDuration(ms)` — human-readable duration
  - `groupLogsByLevel(entries)` — group by level
  - `searchLogs(entries, query)` — full-text search

### Task 6: Backend Log Endpoints

Ensure backend supports all log features:

- Verify `GET /api/v2/tasks/{id}/logs` returns structured logs
- Verify `GET /api/v2/tasks/{id}/events` works for SSE
- Add `GET /api/v2/logs/search` for full-text search
- Add `GET /api/v2/logs/errors` for error aggregation
- Ensure logs include: timestamp, level, source, message, context

## Verification

After execution:
1. `/logs` page loads with task selector
2. Historical logs display correctly
3. Live log streaming works via WebSocket
4. Log filters work (level, source, time, text)
5. Error viewer shows grouped errors with stack traces
6. Debug mode visualizes registration flow step-by-step
7. Network log shows HTTP requests/responses
8. Log export downloads correctly
9. All views are responsive and performant
