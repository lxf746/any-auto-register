# Phase 3: Typed Config - Plan

**Created:** 2026-06-26
**Status:** Ready for execution

## Tasks

### T3.1: Create MailboxConfig base dataclass
- Create `core/mailbox/config.py` with MailboxConfig base dataclass
- Fields: proxy: str | None = None

### T3.2: Create per-provider config dataclasses
- LaoudoConfig(MailboxConfig): auth_token, email, account_id, api_url
- AitreConfig(MailboxConfig): email, api_url
- TempMailLolConfig(MailboxConfig): api_url
- TempMailWebConfig(MailboxConfig): base_url
- DuckMailConfig(MailboxConfig): api_url, provider_url, bearer
- CFWorkerConfig(MailboxConfig): api_url, admin_token, domain, fingerprint
- MoeMailConfig(MailboxConfig): api_url, username, password, session_token
- FreemailConfig(MailboxConfig): api_url, admin_token, username, password
- TestmailConfig(MailboxConfig): api_url, api_key, namespace, tag_prefix
- DDGEmailConfig(MailboxConfig): bearer, imap_host, imap_user, imap_pass

### T3.3: Update from_config() to use config dataclasses
- Update each provider's from_config() to create config dataclass from dict
- Add validation in __post_init__ for required fields

### T3.4: Update __init__.py exports
- Export all config classes from core/mailbox/__init__.py

### T3.5: Verify and cleanup
- Verify all modules parse correctly

## Success Criteria

1. Базовый MailboxConfig dataclass определён ✓
2. Per-provider dataclass'ы для каждого провайдера ✓
3. Валидация конфигурации при создании провайдера ✓
4. Все поля имеют значения по умолчанию ✓

## Dependencies

Phase 1 (Module Split) — Complete
Phase 2 (Unified Registry) — Complete

## Risk

Low — adding type safety, no behavior changes.
