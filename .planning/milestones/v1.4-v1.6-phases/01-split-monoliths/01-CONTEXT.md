# Phase 1: Split Monoliths - Context

**Gathered:** 2026-06-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Разделить монолитные файлы на модули с单一 ответственностью. Каждый файл должен быть < 300 строк.

**Целевые файлы:**
- core/base_sms.py (1304 строк) → base.py, sms_activate.py, herosms.py, smsbower.py, cache.py, controller.py, factory.py
- platforms/chatgpt/browser_register.py (3908 строк) → selectors.py, state_machine.py, otp_flow.py, phone_challenge.py, consent_flow.py, about_you_flow.py, proxy_config.py, main class
- core/db.py (771 строк) → models.py, encryption.py, migrations.py, engine.py
- application/tasks.py (954 строк) → task_runner.py, task_scheduler.py, task_repository.py
- core/account_graph.py (1056 строк) → credentials.py, graph_ops.py, migration.py, overview.py

</domain>

<decisions>
## Implementation Decisions

### Разделение base_sms.py
- base.py: ABC SmsProvider + базовые типы
- sms_activate.py: SmsActivateProvider
- herosms.py: HeroSmsProvider
- smsbower.py: SmsBowerProvider
- cache.py: Кэш для HeroSMS (дедупликация, кандидаты)
- controller.py: PhoneCallbackController
- factory.py: create_sms_provider()

### Разделение chatgpt/browser_register.py
- selectors.py: CSS/XPath селекторы
- state_machine.py: Машина состояний регистрации
- otp_flow.py: Логика OTP/邮箱 верификации
- phone_challenge.py: Телефонный вызов
- consent_flow.py: Согласие на обработку данных
- about_you_flow.py: Заполнение "About You"
- proxy_config.py: Конфигурация прокси
- main.py: ChatGPTBrowserRegister класс

### Разделение db.py
- models.py: SQLModel таблицы
- encryption.py: Шифрование (Fernet)
- migrations.py: Миграции
- engine.py: Engine setup

### Разделение tasks.py
- task_runner.py: Запуск задач
- task_scheduler.py: Планировщик
- task_repository.py: Хранилище задач

### Разделение account_graph.py
- credentials.py: Извлечение учётных данных
- graph_ops.py: Операции с графом аккаунтов
- migration.py: Миграция токенов
- overview.py: Управление обзором

</decisions>

<code_context>
## Existing Code Insights

Кодовая база стабильна после v1.4. Публичный API должен быть сохранён — импорты не должны измениться.

</code_context>

<specifics>
## Specific Ideas

Следовать принцип单一 ответственности. Каждый новый модуль должен иметь чёткую функцию.

</specifics>

<deferred>
## Deferred Ideas

Нет

</deferred>
