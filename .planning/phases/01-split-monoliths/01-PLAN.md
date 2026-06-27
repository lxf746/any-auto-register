# Phase 1: Split Monoliths - Plan

**Created:** 2026-06-27
**Status:** Ready for execution

## Tasks

### T1.1: Split base_sms.py (1304 → 7 modules)
- Create core/sms/ package
- Extract ABC to base.py
- Extract SmsActivateProvider to sms_activate.py
- Extract HeroSmsProvider to herosms.py
- Extract SmsBowerProvider to smsbower.py
- Extract cache logic to cache.py
- Extract PhoneCallbackController to controller.py
- Extract factory to factory.py
- Update imports in core/base_sms.py to re-export

### T1.2: Split chatgpt/browser_register.py (3908 → 8 modules)
- Create platforms/chatgpt/registration/ package
- Extract selectors to selectors.py
- Extract state machine to state_machine.py
- Extract OTP flow to otp_flow.py
- Extract phone challenge to phone_challenge.py
- Extract consent flow to consent_flow.py
- Extract about you flow to about_you_flow.py
- Extract proxy config to proxy_config.py
- Keep main class in browser_register.py

### T1.3: Split db.py (771 → 4 modules)
- Create core/db/ package
- Extract models to models.py
- Extract encryption to encryption.py
- Extract migrations to migrations.py
- Extract engine to engine.py
- Update core/db.py to re-export

### T1.4: Split tasks.py (954 → 3 modules)
- Create application/tasks/ package
- Extract task runner to task_runner.py
- Extract task scheduler to task_scheduler.py
- Extract task repository to task_repository.py
- Update application/tasks.py to re-export

### T1.5: Split account_graph.py (1056 → 4 modules)
- Create core/account_graph/ package
- Extract credentials to credentials.py
- Extract graph ops to graph_ops.py
- Extract migration to migration.py
- Extract overview to overview.py
- Update core/account_graph.py to re-export

## Success Criteria

1. Каждый файл < 300 строк ✓
2. Импорты не изменились (публичный API сохранён) ✓
3. Все модули парсятся без ошибок ✓
4. Тесты проходят (если есть) ✓

## Dependencies

None — this is the first phase.

## Risk

Medium — large refactoring, but well-defined scope.
