# Roadmap: v1.5 Enterprise Cleanup

**Created:** 2026-06-27
**Phases:** 4
**Requirements:** 15 mapped

## Phase 1: Split Monoliths

**Goal:** Разделить монолитные файлы на модули с单一 ответственностью

**Requirements:**
- SPLIT-01: base_sms.py → 7 модулей
- SPLIT-02: chatgpt/browser_register.py → 8 модулей
- SPLIT-03: db.py → 4 модуля
- SPLIT-04: tasks.py → 3 модуля
- SPLIT-05: account_graph.py → 4 модуля

**Success Criteria:**
1. Каждый файл < 300 строк
2. Импорты не изменились (публичный API сохранён)
3. Все модули парсятся без ошибок
4. Тесты проходят (если есть)

---

## Phase 2: Extract Patterns

**Goal:** Выделить общие паттерны в переиспользуемые модули

**Requirements:**
- PATT-01: ManagedSession mixin
- PATT-02: BasePollingMailbox
- PATT-03: Retry/backoff utility
- PATT-04: make_provider_resource() factory

**Success Criteria:**
1. ManagedSession используется в 8+ файлах
2. BasePollingMailbox используется в 13 провайдерах
3. Retry utility используется в 5+ файлах
4. Дублирование кода сокращено на 400+ строк

---

## Phase 3: Merge Duplicates

**Goal:** Объединить дублирующие директории и убрать конфуз

**Requirements:**
- MERG-01: Consolidate core/mailbox/ vs providers/mailbox/
- MERG-02: Убрать дублирующие провайдеры

**Success Criteria:**
1. Единый canonical location для mailbox провайдеров
2. Нет дублирующих файлов
3. Все импорты работают корректно

---

## Phase 4: Type Safety

**Goal:** Добавить типизацию и заменить Any на конкретные типы

**Requirements:**
- TYPE-01: Type hints для BasePlatform
- TYPE-02: Replace Any в RegistrationContext
- TYPE-03: Replace Any в IdentityMaterial
- TYPE-04: Add from_config к BaseMailbox ABC

**Success Criteria:**
1. Все методы BasePlatform имеют type hints
2. RegistrationContext не содержит Any
3. IdentityMaterial не содержит Any
4. BaseMailbox имеет abstract from_config
5. mypy/ruff check проходит без ошибок
