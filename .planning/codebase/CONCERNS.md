# Codebase Concerns

**Analysis Date:** 2026-06-26

## Tech Debt

**Deprecated Module Still Imported:**
- Issue: `core/provider_drivers.py` is marked as deprecated (line 1: `"""provider_drivers — deprecated, everything is read from DB."""`) but the file still exists. While it contains no code, its presence is confusing.
- Files: `core/provider_drivers.py`
- Impact: Dead code in codebase. Any import of this module would be a silent no-op, confusing developers.
- Fix approach: Delete the file. Verify no imports reference it via grep.

**Duplicate `_utcnow` Functions:**
- Issue: `_utcnow()` helper function is independently defined in at least 4 separate files with identical implementations:
  - `core/db.py:12`
  - `core/lifecycle.py:21`
  - `core/account_graph.py:76`
  - `application/tasks.py:56`
- Files: `core/db.py`, `core/lifecycle.py`, `core/account_graph.py`, `application/tasks.py`
- Impact: DRY violation. If timezone handling changes, 4+ places must be updated.
- Fix approach: Consolidate into `core/datetime_utils.py` (which already exists) and import from there everywhere.

**Duplicate `_utcnow_iso` and `_utcnow_ts` Helpers:**
- Issue: Same duplication pattern extends to `_utcnow_iso()` and `_utcnow_ts()` in `core/lifecycle.py` and `application/tasks.py`.
- Files: `core/lifecycle.py`, `application/tasks.py`
- Impact: Same as above — drift risk.
- Fix approach: Move all datetime helpers to `core/datetime_utils.py`.

**Legacy Schema Migration Still Runs on Every Startup:**
- Issue: `core/db.py:_migrate_legacy_accounts_schema()` (line 363) runs raw SQL to migrate a legacy `accounts` table schema on every `init_db()` call. It drops and recreates the `accounts` table using `PRAGMA foreign_keys=OFF`. This was a one-time migration but executes indefinitely.
- Files: `core/db.py:363-427`, `core/db.py:430-446`
- Impact: Unnecessary overhead on every startup. Risk of data loss if migration logic has bugs that manifest on repeated runs. `PRAGMA foreign_keys=OFF` is dangerous if interleaved with concurrent access.
- Fix approach: Add a version/migration tracking table. Run legacy migrations only once, then skip.

**Legacy Provider Key Migration Runs on Every Startup:**
- Issue: `core/db.py:_migrate_legacy_provider_keys()` (line 519) and `_cleanup_non_real_providers()` (line 608) run on every startup to remap old provider keys.
- Files: `core/db.py:519-606`, `core/db.py:608-636`
- Impact: Same as above — idempotent but wasteful. Database writes on every boot.
- Fix approach: Gate behind a migration version flag.

**Large Monolithic Files:**
- Issue: Several files exceed 1000 lines, making them difficult to maintain and test:
  - `platforms/chatgpt/browser_register.py` — 3908 lines
  - `core/base_mailbox.py` — 2059 lines
  - `platforms/windsurf/browser_register.py` — 1987 lines
  - `platforms/chatgpt/register.py` — 1586 lines
  - `platforms/kiro/core.py` — 1429 lines
  - `core/base_sms.py` — 1265 lines
  - `services/turnstile_solver/api_solver.py` — 1138 lines
  - `customer_portal_api/app/services/portal.py` — 1116 lines
  - `core/account_graph.py` — 1060 lines
- Files: (listed above)
- Impact: High cognitive load. Hard to reason about. Merge conflicts likely. Testing individual behaviors is difficult.
- Fix approach: `core/base_mailbox.py` should be split per-provider (each provider already has its own file under `providers/mailbox/`). `core/base_sms.py` similarly. `platforms/chatgpt/browser_register.py` could be split into registration steps (email, password, OTP, phone, trial).

**`base_platform.py` God Class with Capability Dispatch:**
- Issue: `_handle_capability()` (line 203) is a large if/elif chain dispatching to ~10 different capability handlers. Each handler is a separate method but they all live in one 504-line class.
- Files: `core/base_platform.py:203-233`
- Impact: Adding a new capability requires modifying this central dispatcher. Single Responsibility Principle violated.
- Fix approach: Use a registry/dispatch dict or plugin pattern for capability handlers.

## Security Concerns

**CRITICAL: Password Comparison Not Timing-Safe in Main API Auth:**
- Issue: `api/auth.py:27` compares passwords using plain `==` operator: `if body.password == password:`. This is vulnerable to timing attacks. The customer portal (`customer_portal_api/app/security.py`) correctly uses `hmac.compare_digest`, but the main API does not.
- Files: `api/auth.py:27`
- Impact: An attacker can statistically determine the password character-by-character by measuring response time differences.
- Fix approach: Use `hmac.compare_digest(body.password, password)` or `secrets.compare_digest()`.

**CRITICAL: Auth Middleware Returns Password as JWT Token:**
- Issue: `api/auth.py:28` returns the raw password as the "token": `return {"ok": True, "token": password}`. The auth middleware (`core/auth.py:41`) then compares `auth_header[7:] == password` — essentially using the password as both credential and token. This means the password is transmitted in every API request header.
- Files: `api/auth.py:28`, `core/auth.py:41`
- Impact: The password circulates as a bearer token in every request. If intercepted (even via logs), it exposes the full password. No token expiry, no refresh mechanism.
- Fix approach: Generate a random session token on login. Store password hashes, never return passwords as tokens.

**CRITICAL: Default JWT Secret in Production Config:**
- Issue: `customer_portal_api/app/config.py:9` has `jwt_secret: str = os.getenv("PORTAL_JWT_SECRET", "change-me-in-production")`. If the env var is not set, all JWTs are signed with a well-known secret.
- Files: `customer_portal_api/app/config.py:9`
- Impact: Any attacker can forge valid JWTs for any user by signing with `"change-me-in-production"`.
- Fix approach: Fail startup if `PORTAL_JWT_SECRET` is not set or is the default value.

**CRITICAL: Default Admin Credentials in Production:**
- Issue: `customer_portal_api/app/config.py:12-13` seeds admin with `username: "admin"`, `password: "admin123456"`.
- Files: `customer_portal_api/app/config.py:12-13`
- Impact: If env vars are not overridden, the admin account is trivially compromisable.
- Fix approach: Require explicit env vars for admin credentials. Fail startup if using defaults in non-development mode.

**HIGH: CORS Allows All Origins:**
- Issue: `main.py:99` sets `allow_origins=["*"]` for CORS. `customer_portal_api/main.py:26` defaults to `settings.cors_origins or ["*"]`.
- Files: `main.py:97-102`, `customer_portal_api/main.py:25-26`
- Impact: Any website can make authenticated API requests to this server (if cookies are used). Combined with the password-as-cookie auth, this is a CSRF vulnerability.
- Fix approach: Restrict CORS to specific origins. At minimum, do not use `*` when auth uses cookies.

**HIGH: Passwords Stored in Plaintext in Database:**
- Issue: `core/db.py:31` stores `password: str` directly. The `save_account()` function (line 303) writes `account.password` directly to the database without hashing.
- Files: `core/db.py:31`, `core/db.py:314`
- Impact: If the SQLite database file is accessed, all account passwords are readable in plaintext.
- Fix approach: Encrypt or hash passwords at rest. The customer portal uses PBKDF2 (`customer_portal_api/app/security.py:26-30`), but the main app does not.

**HIGH: TLS Verification Disabled by Default:**
- Issue: `core/tls.py:19-23` provides `insecure_request()` which calls `verify=False` by default. `mark_session_insecure()` (line 26) sets `session.verify = False`.
- Files: `core/tls.py:19-33`
- Impact: Many HTTP requests throughout the codebase silently skip TLS certificate verification, making them vulnerable to MITM attacks.
- Fix approach: Make TLS verification opt-in only, not the default. Log warnings when verification is disabled.

**MEDIUM: SQL Injection Risk in `_ensure_column`:**
- Issue: `core/db.py:458` uses f-string interpolation in raw SQL: `conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")`. While `table` and `column` come from internal callers (not user input), this is a dangerous pattern.
- Files: `core/db.py:448-458`
- Impact: If any future caller passes user-controlled values, SQL injection becomes possible.
- Fix approach: Validate table/column names against allowlists or use parameterized queries.

**MEDIUM: Subprocess Shell Commands in Solver Manager:**
- Issue: `services/solver_manager.py:189-201` runs `netstat` and `lsof` commands via `subprocess.check_output()`. While the commands use list arguments (not shell=True), the `lsof` output is parsed without sanitization.
- Files: `services/solver_manager.py:189-201`
- Impact: Low risk since it only kills local processes, but the pattern of parsing subprocess output is fragile.
- Fix approach: Use `psutil` library for cross-platform process management.

**LOW: No Rate Limiting on Auth Endpoints:**
- Issue: `api/auth.py:22-29` has no rate limiting on the login endpoint. An attacker can brute-force the password.
- Files: `api/auth.py:22-29`
- Impact: Password brute-force is trivially possible, especially since the password is a simple string.
- Fix approach: Add rate limiting middleware (e.g., slowapi) or lockout mechanism.

## Code Quality Issues

**Bare `except:` Clause (No Exception Type):**
- Issue: `services/turnstile_solver/api_solver.py:825` uses bare `except:` (no exception type specified), which catches `KeyboardInterrupt`, `SystemExit`, and all other exceptions including `GeneratorExit`.
- Files: `services/turnstile_solver/api_solver.py:825`
- Impact: Swallows `KeyboardInterrupt` and `SystemExit`, making the process harder to terminate.
- Fix approach: Change to `except Exception:`.

**Excessive Bare `except Exception:` With Silent Swallowing:**
- Issue: There are 643+ occurrences of `except Exception` across the codebase. Many silently swallow errors without logging, especially in:
  - `services/solver_manager.py` (8 bare handlers)
  - `services/turnstile_solver/api_solver.py` (20+ handlers, many with just `pass`)
  - `platforms/windsurf/browser_register.py` (20+ handlers)
  - `platforms/trae/browser_register.py` (12+ handlers)
- Files: (all listed above)
- Impact: Errors are silently lost. Debugging production issues becomes extremely difficult. Bugs in these paths will never surface.
- Fix approach: At minimum, add `logger.debug()` or `logger.warning()` in every except block. Use specific exception types where possible.

**Scheduler Loads All Accounts Into Memory:**
- Issue: `core/scheduler.py:48` loads ALL accounts into memory with `s.exec(select(AccountModel)).all()`. For large account databases, this will cause memory issues.
- Files: `core/scheduler.py:48`
- Impact: OOM risk with 100K+ accounts. No pagination or batching.
- Fix approach: Use cursor-based pagination or limit the query.

**Thread-Unsafe Global State in solver_manager.py:**
- Issue: `services/solver_manager.py:12` uses a global `_proc` variable that is accessed and modified from multiple threads (main thread, daemon threads, signal handlers).
- Files: `services/solver_manager.py:12-13`
- Impact: Race conditions. `_proc` could be set to `None` by `stop()` while `start()` is checking it.
- Fix approach: All access to `_proc` should be under `_lock`, which is partially done but not consistently (e.g., `is_running()` reads `_proc` at line 23 without the lock).

**Task Locks Dictionary Never Cleaned Up:**
- Issue: `application/tasks.py:52` creates a `_task_locks` dictionary that grows with each task ID but never removes entries.
- Files: `application/tasks.py:52-53`, `application/tasks.py:78-84`
- Impact: Memory leak over time. Each unique task ID creates a permanent `threading.Lock` entry.
- Fix approach: Use `WeakValueDictionary` or periodically clean up locks for completed tasks.

**`print()` Used for Logging Instead of `logging` Module:**
- Issue: Many files use `print()` for output instead of the `logging` module:
  - `core/db.py:459,571,605`
  - `core/scheduler.py:30,40,63`
  - `core/base_mailbox.py:84,88,93,694,847,861,949,1180,1185,1386,1391,1418,1420,1457,1459,1607,1940,1990,2040,2045`
  - `services/task_runtime.py:36,41`
- Files: (listed above)
- Impact: No log levels, no structured logging, no way to filter/suppress output in production.
- Fix approach: Replace all `print()` calls with `logger.info()`/`logger.debug()`/`logger.error()`.

**Magic Numbers Without Constants:**
- Issue: `core/scheduler.py:42` uses `time.sleep(3600)` (1 hour). `core/lifecycle.py:492` uses `time.sleep(30)`. `core/base_sms.py:162,166,170` use `time.sleep(3)`. These are undocumented magic numbers.
- Files: `core/scheduler.py:42`, `core/lifecycle.py:492`, `core/base_sms.py:162,166,170`
- Impact: Hard to tune behavior. Easy to accidentally change the wrong sleep value.
- Fix approach: Define as named constants (e.g., `POLL_INTERVAL_SECONDS = 3600`).

## Missing Tests

**Platform Registration Flows Untested:**
- Issue: 14 platform directories exist (`chatgpt`, `windsurf`, `kiro`, `cursor`, `trae`, `blackbox`, `blink`, `cerebras`, `fireworks`, `grok`, `kimchi`, `openblocklabs`, `tavily`, `anything`) but only 2 have test files:
  - `tests/test_windsurf_platform.py` (526 lines)
  - `tests/test_chatgpt_oauth_requirements.py` (exists but small)
- Files: `platforms/*/plugin.py`, `platforms/*/browser_register.py`
- Impact: 12 out of 14 platforms have zero test coverage for their core registration logic. Changes to `base_platform.py` could break platforms without detection.
- Priority: **High** — Platform plugins are the core business logic.

**Core Services Untested:**
- Issue: No test files exist for:
  - `core/db.py` (641 lines, complex migration logic)
  - `core/lifecycle.py` (527 lines)
  - `core/account_graph.py` (1060 lines)
  - `core/scheduler.py` (114 lines)
  - `services/task_runtime.py` (101 lines)
  - `services/solver_manager.py` (228 lines)
  - All files under `customer_portal_api/`
- Files: (listed above)
- Impact: Critical infrastructure code has no regression protection. Database migrations, account graph sync, and task orchestration are untested.
- Priority: **High** — Database and lifecycle logic are critical paths.

**Provider Implementations Untested:**
- Issue: 12+ mailbox providers, 2 SMS providers, and 3 captcha providers exist under `providers/` but only `test_sms_provider.py` and `test_herosms_api.py` have tests.
- Files: `providers/mailbox/*.py`, `providers/sms/*.py`, `providers/captcha/*.py`
- Impact: Provider bugs (especially around auth, retries, and edge cases) will only be caught in production.
- Priority: **Medium** — Providers are external-facing and frequently change.

**API Endpoints Largely Untested:**
- Issue: 16 API routers exist under `api/` but only basic tests exist for a few:
  - `test_api_accounts.py`, `test_api_health.py`, `test_api_lifecycle.py`, `test_api_platforms.py`, `test_api_proxies.py`, `test_api_stats.py`
  - Missing tests for: `api/auth.py`, `api/config.py`, `api/proxies.py`, `api/sms.py`, `api/system.py`, `api/task_commands.py`, `api/task_logs.py`
- Files: `api/*.py`
- Impact: API contract changes and regressions go undetected.
- Priority: **Medium**

**No Integration Tests:**
- Issue: There are no integration tests that verify the full flow: API request → application service → database persistence → response.
- Files: `tests/conftest.py` (sets up TestClient but no integration tests use it)
- Impact: Component interactions are untested. The TestClient infrastructure exists but is underutilized.
- Priority: **Medium**

**No E2E / Browser Tests:**
- Issue: No Playwright or Camoufox end-to-end tests exist despite the codebase heavily relying on browser automation.
- Files: N/A
- Impact: Browser registration flows (the core product value) have zero automated verification.
- Priority: **Medium** (browser tests are expensive to maintain)

## Dependency Risks

**Unpinned Dependencies:**
- Issue: `requirements.txt` uses only `>=` constraints (e.g., `fastapi>=0.110.0`, `playwright>=1.43.0`). No upper bounds or lockfile.
- Files: `requirements.txt`
- Impact: A major version bump in any dependency (e.g., FastAPI 1.0, Pydantic 3.0) could silently break the application. `curl_cffi>=0.6.0` is particularly risky as it's a C extension with breaking API changes.
- Fix approach: Pin exact versions or use ranges with upper bounds (e.g., `fastapi>=0.110,<1.0`). Generate a lockfile.

**Heavy Browser Automation Dependencies:**
- Issue: The app depends on `playwright`, `patchright`, `camoufox`, and `quart` (for the solver) — all heavy browser automation tools with native binaries.
- Files: `requirements.txt:6,12,10,13`
- Impact: Docker image is large (Chromium + Camoufox + Playwright browsers). Build times are long. Each tool updates independently with potential breaking changes.
- Fix approach: Pin browser versions. Consider if all four browser tools are necessary.

**SQLite as Production Database:**
- Issue: The entire application uses SQLite (`core/db.py:22`) even in production Docker deployments.
- Files: `core/db.py:22`, `docker-compose.yml:10`
- Impact: SQLite does not support concurrent writes well. The `check_same_thread=False` setting in tests (`tests/conftest.py:26`) indicates threading issues. The `_kill_by_port` pattern in `solver_manager.py` suggests awareness of concurrency issues.
- Fix approach: For production deployments with multiple workers or high concurrency, consider PostgreSQL.

**`pyinstaller` as Runtime Dependency:**
- Issue: `requirements.txt:15` includes `pyinstaller>=6.0.0` as a production dependency, but it's only needed for building executables.
- Files: `requirements.txt:15`
- Impact: Unnecessarily inflates the Docker image and install time.
- Fix approach: Move to a separate `[build]` or `[dev]` requirements group.

## Scalability Concerns

**Single-Process SQLite Architecture:**
- Issue: The entire backend runs as a single FastAPI process with SQLite. `core/scheduler.py`, `core/lifecycle.py`, `application/tasks.py`, and `services/task_runtime.py` all share the same database file.
- Files: `core/db.py`, `main.py`
- Impact: Cannot scale horizontally. A single heavy registration task can block the scheduler. The `_task_locks` dictionary (`application/tasks.py:52`) grows unboundedly.
- Fix approach: For single-server use, this is acceptable. For multi-server, migrate to PostgreSQL with proper connection pooling.

**Task Runtime Thread Pool Limitations:**
- Issue: `services/task_runtime.py:19` defaults to `max_parallel_tasks=3` and `max_parallel_per_platform=1`. The thread pool is unbounded — each task spawns a new `threading.Thread`.
- Files: `services/task_runtime.py:19,67-72`
- Impact: Under load, many threads could be created simultaneously. No backpressure mechanism.
- Fix approach: Use `ThreadPoolExecutor` with bounded pool size instead of spawning raw threads.

**Scheduler Loads All Accounts:**
- Issue: `core/scheduler.py:48` loads all accounts into memory for trial expiry check. `core/lifecycle.py:48-51` does the same for validity checks with only a `limit=100` default.
- Files: `core/scheduler.py:48`, `core/lifecycle.py:48-51`
- Impact: With 10K+ accounts, each scheduler tick processes a large dataset. No incremental processing.
- Fix approach: Process in batches. Use database-level filtering for trial expiry (WHERE clause) instead of loading all and filtering in Python.

**No Database Connection Pooling:**
- Issue: `core/db.py:22` creates a single engine with default SQLite settings. `get_session()` (line 639) yields sessions without connection pooling configuration.
- Files: `core/db.py:22,639-641`
- Impact: Each `Session(engine)` creates a new connection. Under concurrent requests, SQLite file locking becomes a bottleneck.
- Fix approach: Use `StaticPool` or configure `pool_size` for SQLite. Consider migrating to PostgreSQL for production.

## Areas Needing Refactoring

**Account Graph Module (1060 lines):**
- Issue: `core/account_graph.py` handles credential management, provider account linking, resource tracking, overview management, and legacy migration all in one file. It has 15+ exported functions.
- Files: `core/account_graph.py`
- Why it needs refactoring: High cognitive load. Changes to credential handling risk breaking provider account logic. No clear module boundaries.
- Suggested split: `core/account_credentials.py`, `core/account_overview.py`, `core/account_providers.py`, `core/account_migration.py`.

**Base Mailbox Module (2059 lines):**
- Issue: `core/base_mailbox.py` contains 10+ concrete mailbox provider implementations (mail.tm, tempyemail, tempmail.lol, cfworker, moemail, freemail, duckmail, ddg_email, aitre, laoudo) plus the abstract base class.
- Files: `core/base_mailbox.py`
- Why it needs refactoring: A single 2000+ line file with 10+ unrelated providers makes maintenance painful. Each provider has its own API, auth, and error handling.
- Suggested split: Move each provider implementation to its own file under `providers/mailbox/` (which already exists with partial implementations).

**Base SMS Module (1265 lines):**
- Issue: `core/base_sms.py` contains HeroSMS, SMSActivate, and SMSBower implementations plus the base class.
- Files: `core/base_sms.py`
- Why it needs refactoring: Same as mailbox — multiple unrelated providers in one file.
- Suggested split: Each SMS provider to its own file under `providers/sms/`.

**ChatGPT Browser Registration (3908 lines):**
- Issue: `platforms/chatgpt/browser_register.py` is the single largest file in the codebase, handling email input, password input, OTP, phone verification, account setup, and trial activation all in one class.
- Files: `platforms/chatgpt/browser_register.py`
- Why it needs refactoring: Impossible to unit test individual steps. Changes to phone verification logic risk breaking email flow.
- Suggested split: Extract step classes: `EmailStep`, `PasswordStep`, `OTPStep`, `PhoneStep`, `TrialStep`.

**Customer Portal Service (1116 lines):**
- Issue: `customer_portal_api/app/services/portal.py` contains ALL business logic for the customer portal: user management, role management, platform access, orders, payments, tasks, accounts, proxies, configs.
- Files: `customer_portal_api/app/services/portal.py`
- Why it needs refactoring: Single class handles 15+ distinct business domains. Impossible to test in isolation.
- Suggested split: `UserService`, `RoleService`, `OrderService`, `PaymentService`, `TaskService`, `AccountService`, `ProxyService`, `ConfigService`.

---

*Concerns audit: 2026-06-26*
