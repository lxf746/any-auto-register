# Phase 3: Account Endpoints - Context

**Gathered:** 2026-06-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Полный набор Account CRUD, export, import, check эндпоинтов работает в v2.

</domain>

<decisions>
## Implementation Decisions

### Account CRUD
- Create, update, delete, get by ID
- Используем существующий AccountsService из application/accounts.py

### Account Exports
- CSV, JSON, sub2api, cpa, kiro-go, any2api форматы
- Используем существующий service.export_csv, service.export_json

### Account Imports
- Загрузка аккаунтов из файлов
- Используем service.import_accounts

### Account Checks
- check-all и check-one проверяют статус аккаунтов
- Используем существующий account_checks.py

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
