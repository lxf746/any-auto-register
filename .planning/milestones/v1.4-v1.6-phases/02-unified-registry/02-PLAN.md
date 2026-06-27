# Phase 2: Unified Registry - Plan

**Created:** 2026-06-26
**Status:** Ready for execution

## Tasks

### T2.1: Add from_config() to mailbox providers
- Add `from_config(cls, config: dict)` classmethod to each provider class in `core/mailbox/*.py`
- Each from_config() should extract provider-specific keys from config dict

### T2.2: Update create_mailbox() to use unified registry
- Replace `MAILBOX_FACTORY_REGISTRY.get(lookup_key)` with `create_provider("mailbox", lookup_key, resolved_extra)` from `providers/registry.py`
- Keep fallback chain logic in create_mailbox()

### T2.3: Remove MAILBOX_FACTORY_REGISTRY
- Remove MAILBOX_FACTORY_REGISTRY from `core/mailbox/registry.py`
- Remove all `_create_*` factory functions from `core/mailbox/registry.py`
- Keep create_mailbox() but update it to use unified registry

### T2.4: Update base_mailbox.py re-exports
- Remove re-exports of MAILBOX_FACTORY_REGISTRY and _create_* functions
- Keep re-exports of create_mailbox and provider classes

### T2.5: Verify and cleanup
- Verify imports work
- Run any existing tests

## Success Criteria

1. ProviderRegistry класс取代ляет MAILBOX_FACTORY_REGISTRY и _registry["mailbox"] ✓
2. Декоратор @register_provider работает для всех типов провайдеров ✓
3. create_provider() фабрика использует from_config() classmethod ✓
4. Автоматическое обнаружение провайдеров при импорте core/mailbox ✓

## Dependencies

Phase 1 (Module Split) — Complete

## Risk

Low — restructuring registry, no behavior changes.
