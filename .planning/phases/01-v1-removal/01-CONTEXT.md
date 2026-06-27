# Phase 1: v1 Removal - Context

**Gathered:** 2026-06-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Удалить старый frontend/ (Vite+React), static/, v1 API эндпоинты и все шимы/compat слои. Проект не должен содержать dual-кода.

</domain>

<decisions>
## Implementation Decisions

### Scope of Removal
- frontend/ — entire directory (Vite+React SPA)
- static/ — build output of old frontend
- api/auth.py, api/accounts.py, и все v1 API файлы
- Все шимы и compat слои между v1 и v2

### the agent's Discretion
All implementation choices are at the agent's discretion — discuss phase was skipped per user setting. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

</decisions>

<code_context>
## Existing Code Insights

Codebase context will be gathered during plan-phase research.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — discuss phase skipped. Refer to ROADMAP phase description and success criteria.

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
