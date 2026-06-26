# Coding Conventions

**Analysis Date:** 2026-06-26

## Naming Patterns

**Files:**
- `snake_case.py` for all Python modules (e.g., `base_platform.py`, `accounts_repository.py`, `task_commands.py`)
- Platform plugins live in `platforms/{name}/plugin.py` with supporting modules like `core.py`, `protocol_mailbox.py`, `browser_register.py`

**Classes:**
- `PascalCase` (e.g., `BasePlatform`, `AccountsService`, `AccountCreateCommand`, `MailTmMailbox`)
- Service classes: `{Entity}Service` (e.g., `AccountsService`, `HealthService`, `ActionsService`)
- Repository classes: `{Entity}Repository` (e.g., `AccountsRepository`, `ProviderSettingsRepository`)
- Domain dataclasses: `{Entity}Record`, `{Entity}Query`, `{Entity}CreateCommand`, `{Entity}UpdateCommand` (e.g., `AccountRecord`, `AccountQuery`, `AccountCreateCommand`)
- Database models: `{Entity}Model` (e.g., `AccountModel`, `AccountOverviewModel`, `TaskModel`)
- Request DTOs in API layer: `{Entity}Request` (e.g., `AccountCreateRequest`, `RegisterTaskRequest`)

**Functions:**
- `snake_case` throughout (e.g., `list_accounts`, `create_register_task`, `solve_turnstile_with_fallback`)
- Private/internal methods prefixed with `_` (e.g., `_make_random_password`, `_resolve_identity`, `_serialize`)
- Factory functions: `create_{thing}` (e.g., `create_provider`, `create_sms_provider`, `create_proxy_provider`)
- Boolean queries: `is_*`, `has_*`, `_should_*` (e.g., `_should_require_identity_email`, `has_cursor_valid_payment_method`)

**Variables:**
- `snake_case` (e.g., `provider_key`, `account_id`, `captcha_solver`)
- Module-level registries: `_registry` (underscore-prefixed private global)
- Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_MAILTM_API_URL`, `SMS_ACTIVATE_SERVICES`, `IMPORT_LINE_RE`)

## Code Style

**Formatting:**
- No configured formatter (no black, ruff, or autopep8 config detected)
- Generally follows PEP 8 with some flexibility on line length
- 4-space indentation throughout
- Trailing commas used in multi-line structures

**Linting:**
- No linter config detected (no `.flake8`, `pyproject.toml`, `ruff.toml`, or `setup.cfg`)
- Occasional `# noqa` comments for intentional suppressions (e.g., `# noqa: BLE001` in `providers/registry.py`)

## Import Organization

**Order (consistent across codebase):**
1. `from __future__ import annotations` — present in almost every file
2. Standard library imports (`os`, `sys`, `json`, `time`, `re`, `csv`, etc.)
3. Third-party imports (`fastapi`, `sqlmodel`, `requests`, `pydantic`, etc.)
4. Local imports (`from core.`, `from api.`, `from application.`, `from infrastructure.`, `from domain.`, `from providers.`, `from platforms.`)

**Pattern:**
```python
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from application.accounts import AccountsService
from domain.accounts import AccountCreateCommand, AccountQuery
```

**Path Aliases:**
- No aliases; all imports use explicit relative or absolute paths
- Core/platform imports often use lazy import pattern inside methods to avoid circular dependencies:
```python
def some_method(self):
    from platforms.cursor.browser_oauth import register_with_browser_oauth
    ...
```

**Lazy Imports:**
- Extensively used in `core/base_platform.py` to defer heavy imports (Playwright, browser modules)
- Also used in `main.py` lifespan for scheduler, task_runtime, solver_manager

## Error Handling

**Patterns:**
- `RuntimeError` for business logic failures with descriptive messages:
  ```python
  raise RuntimeError(f"2Captcha task creation failed: {payload}")
  raise RuntimeError("No available Turnstile captcha provider found")
  raise RuntimeError("Browser mode has no default captcha provider configured...")
  ```
- `NotImplementedError` for unimplemented platform features:
  ```python
  raise NotImplementedError(f"{self.display_name} does not support '{self.config.executor_type}' executor yet")
  raise NotImplementedError(f"Platform {self.name} does not support action: {action_id}")
  ```
- `ValueError` for registration/config issues:
  ```python
  raise ValueError(f"{self.display_name} registration flow did not obtain an available email")
  ```
- `HTTPException` in API layer for HTTP error responses:
  ```python
  raise HTTPException(404, "Account not found")
  raise HTTPException(400, str(exc)) from exc
  ```
- Broad `except Exception: pass` used in provider modules for resilience (e.g., mailbox polling loops in `providers/mailbox/mailtm.py`)
- Provider factories raise `RuntimeError` on missing config, `ValueError` on unknown provider, `TypeError` on missing factory method

## Logging Approach

**Framework:** `print()` is the primary logging mechanism; `logging` module used only in `providers/registry.py`

**Patterns:**
- Status prefix: `print(f"[OK] Database initialized")` in `main.py` lifespan
- Platform instances use `self.log(message)` which delegates to `self._log_fn` (defaults to `print`)
- Log function injection: `set_logger(logger)` method on `BasePlatform`
- Test helpers accept `log_fn=logs.append` parameter for log capture
- Provider registry uses `logging.getLogger(__name__)` with `logger.warning(...)`:
  ```python
  logger = logging.getLogger(__name__)
  logger.warning("Failed to load provider module %s: %s", name, exc)
  ```

**Guideline:** Use `print("[OK] ...")` for startup status; use `self.log()` in platform code; use `logging` in infrastructure/provider code.

## Type Annotations

**Style:**
- Uses Python 3.10+ union syntax: `str | None`, `dict | None`, `int | None`
- `from __future__ import annotations` used in almost all files for forward reference support
- Domain dataclasses use `Optional[str]` from typing (older style in `domain/accounts.py`)
- Function signatures fully typed in application/infrastructure layers
- Return types specified: `-> dict`, `-> str | None`, `-> list[str]`, `-> bool`

**Examples from codebase:**
```python
def list_accounts(self, query: AccountQuery) -> dict:
def get_account(self, account_id: int) -> dict | None:
def _make_random_password(self, length: int = 16, charset: Optional[str] = None) -> str:
def get_provider_class(provider_type: str, driver_type: str) -> type | None:
```

**Domain layer uses dataclasses with `slots=True`:**
```python
@dataclass(slots=True)
class AccountRecord:
    id: int
    platform: str
    email: str
    ...
```

**Database models use SQLModel field declarations:**
```python
class AccountModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    platform: str = Field(index=True)
```

## Documentation Style

**Module docstrings:** Present but brief, single-line or short paragraph:
```python
"""Base class for platform plugins"""
"""Platform plugin registry - auto-scan platforms/ directory to load plugins"""
"""Unified provider registry — auto-discovery + factory."""
```

**Function/method docstrings:** Used on public API and important internal methods; not exhaustive:
```python
def check_valid(self, account: Account) -> bool:
    """Check if account is valid"""

def get_platform_actions(self) -> list:
    """
    Return platform-supported extra operation list, each item format:
    {"id": str, "label": str, "params": [{"key": str, "label": str, "type": str}]}
    """
```

**Inline comments:** Used to explain non-obvious logic, workarounds, or platform-specific behavior:
```python
# Force stdout/stderr to utf-8 (Windows Chinese edition defaults to gbk)
# PyInstaller static-analysis hook — makes modulefinder track Solver subprocess deps
# Keep enabled/default providers even if config is empty — user explicitly turned them on
```

**Not used:** No type stubs, no Sphinx/mkdocstrings, no enforced docstring coverage.

## Module Design

**Exports:**
- Each layer exposes its public API via module-level functions or class instances
- `api/` files define `router = APIRouter(...)` and instantiate service as module-level singleton
- `application/` files define service classes, instantiated at module level in API layer
- `infrastructure/` files define repository classes, instantiated inside service constructors

**Barrel Files:**
- `__init__.py` files are mostly empty or contain a single docstring
- No barrel re-exports; all imports are explicit

**Service Pattern:**
```python
# api/accounts.py
router = APIRouter(prefix="/accounts", tags=["accounts"])
service = AccountsService()

# application/accounts.py
class AccountsService:
    def __init__(self, repository: AccountsRepository | None = None):
        self.repository = repository or AccountsRepository()
```

## Architecture Layer Rules

**Layer dependencies (strict):**
```
api/ → application/ → domain/
                    → infrastructure/ → core/
platforms/ → core/
providers/ → core/
```

- `api/` defines HTTP routes, request/response models; delegates to `application/`
- `application/` contains business logic services; uses `domain/` for DTOs and `infrastructure/` for persistence
- `domain/` contains pure dataclasses (no imports from other layers)
- `infrastructure/` contains repository implementations; uses `core/db.py` for database access
- `core/` contains base classes, shared utilities, database models; no upward dependencies
- `platforms/` contains plugin implementations extending `core/base_platform.py`
- `providers/` contains provider implementations using registry pattern

## Key Patterns to Follow

**When adding a new API endpoint:**
1. Add request/response models in `api/{module}.py` as Pydantic `BaseModel`
2. Add service method in `application/{module}.py`
3. Add repository method in `infrastructure/{module}_repository.py` if persistence needed
4. Add domain dataclass in `domain/{module}.py` if new DTO needed
5. Register router in `main.py` with `app.include_router(router, prefix="/api")`

**When adding a new platform:**
1. Create `platforms/{name}/plugin.py` with class extending `BasePlatform`
2. Use `@register` decorator from `core/registry.py`
3. Implement `check_valid()` (required), `build_*_adapter()` methods (as applicable)
4. Set class attributes: `name`, `display_name`, `version`, `supported_executors`, `supported_identity_modes`

**When adding a new provider:**
1. Create file in `providers/{type}/{name}.py`
2. Use `@register_provider("type", "driver_name")` decorator
3. Implement `from_config(cls, config: dict)` classmethod
4. Extend appropriate base class (`BaseMailbox`, `BaseCaptcha`, etc.)

---

*Convention analysis: 2026-06-26*
