# Phase 2: Extract Patterns - Plan

**Created:** 2026-06-27
**Status:** Ready for execution

## Tasks

### T2.1: ManagedSession mixin
- Create core/mixins/managed_session.py
- Extract common session lifecycle pattern (_get_session, close, __enter__, __exit__)
- Apply to: SmsActivateProvider, HeroSmsProvider, GenericHttpMailbox, FreemailMailbox, MoEmailMailbox, HTTPClient, Any2ApiClient, KiroCore, WindsurfCore, BlinkCore

### T2.2: BasePollingMailbox
- Create core/mailbox/base_polling.py
- Extract common polling pattern (wait_for_code, wait_for_link)
- Template method: subclasses implement _fetch_messages()
- Apply to: 13 mailbox providers

### T2.3: Retry/backoff utility
- Create core/utils/retry.py
- Extract retry/backoff logic
- Apply to: HTTPClient, SMS polling, browser registration, mailbox providers

### T2.4: make_provider_resource() factory
- Create core/mailbox/provider_resource.py
- Extract provider_resource dict construction
- Apply to: 13+ mailbox providers

## Success Criteria

1. ManagedSession используется в 8+ файлах ✓
2. BasePollingMailbox используется в 13 провайдерах ✓
3. Retry utility используется в 5+ файлах ✓
4. Дублирование кода сокращено на 400+ строк ✓

## Dependencies

Phase 1 (Split Monoliths) — Complete

## Risk

Medium — changes affect multiple files, but patterns are well-defined.
