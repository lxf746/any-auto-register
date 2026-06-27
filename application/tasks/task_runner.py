"""Task execution engine and worker logic."""
from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from typing import Any, Callable, Optional

from sqlmodel import Session, select

from core.account_graph import (
    load_account_graphs,
    patch_account_graph,
    recover_lifecycle_status_for_valid_account,
)
from core.base_platform import AccountStatus, RegisterConfig
from core.datetime_utils import _utcnow, _utcnow_iso
from core.db import AccountModel, TaskModel, engine, save_account
from core.platform_accounts import build_platform_account
from core.registry import get
from infrastructure.platform_runtime import PlatformRuntime

from application.tasks.task_repository import (
    TASK_STATUS_CANCELLED,
    TASK_STATUS_CANCEL_REQUESTED,
    TASK_STATUS_FAILED,
    TASK_STATUS_INTERRUPTED,
    TASK_STATUS_RUNNING,
    TASK_STATUS_SUCCEEDED,
    TERMINAL_TASK_STATUSES,
    TASK_TYPE_ACCOUNT_CHECK,
    TASK_TYPE_ACCOUNT_CHECK_ALL,
    TASK_TYPE_PLATFORM_ACTION,
    TASK_TYPE_REGISTER,
    append_task_event,
    mutate_task,
    save_task_log,
    serialize_task,
)


def _bool_config(value: Any, default: bool) -> bool:
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in {"0", "false", "no", "off"}


def _int_config(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _resolve_sms_provider_for_task(extra: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    from infrastructure.provider_definitions_repository import ProviderDefinitionsRepository
    from infrastructure.provider_settings_repository import ProviderSettingsRepository

    settings_repo = ProviderSettingsRepository()
    definitions_repo = ProviderDefinitionsRepository()
    provider_key = str(
        extra.get("sms_provider")
        or extra.get("phone_provider")
        or settings_repo.get_default_provider_key("sms")
        or ""
    ).strip()
    if not provider_key:
        provider_key = "sms_activate" if extra.get("sms_activate_api_key") else ""
    definition = definitions_repo.get_by_key("sms", provider_key) if provider_key else None
    settings = settings_repo.resolve_runtime_settings("sms", provider_key, extra) if definition else dict(extra)
    return provider_key, settings


class TaskLogger:
    def __init__(self, task_id: str):
        self.task_id = task_id

    def log(self, message: str, *, level: str = "info", event_type: str = "log", detail: dict | None = None) -> None:
        append_task_event(
            self.task_id,
            message,
            event_type=event_type,
            level=level,
            detail=detail,
        )
        print(f"[task:{self.task_id}] {message}")

    def mark_running(self) -> None:
        def _update(task: TaskModel) -> None:
            task.status = TASK_STATUS_RUNNING
            task.started_at = task.started_at or _utcnow()

        mutate_task(self.task_id, _update)
        self.log("Task execution started", event_type="state")

    def is_cancel_requested(self) -> bool:
        with Session(engine) as session:
            task = session.get(TaskModel, self.task_id)
            return bool(task and task.status == TASK_STATUS_CANCEL_REQUESTED)

    def set_progress(self, current: int, total: Optional[int] = None) -> None:
        current = max(int(current), 0)

        def _update(task: TaskModel) -> None:
            task.progress_current = current
            if total is not None:
                task.progress_total = max(int(total), 0)

        mutate_task(self.task_id, _update)

    def record_success(self) -> None:
        def _update(task: TaskModel) -> None:
            task.success_count += 1

        mutate_task(self.task_id, _update)

    def record_error(self, error: str) -> None:
        def _update(task: TaskModel) -> None:
            task.error_count += 1
            result = task.get_result()
            errors = list(result.get("errors", []))
            errors.append(error)
            result["errors"] = errors
            task.set_result(result)

        mutate_task(self.task_id, _update)

    def add_cashier_url(self, url: str) -> None:
        def _update(task: TaskModel) -> None:
            result = task.get_result()
            urls = list(result.get("cashier_urls", []))
            urls.append(url)
            result["cashier_urls"] = urls
            task.set_result(result)

        mutate_task(self.task_id, _update)

    def set_result_data(self, data: Any) -> None:
        def _update(task: TaskModel) -> None:
            result = task.get_result()
            result["data"] = data
            task.set_result(result)

        mutate_task(self.task_id, _update)

    def finish(self, status: str, *, error: str = "") -> None:
        def _update(task: TaskModel) -> None:
            task.status = status
            task.finished_at = _utcnow()
            if error:
                task.error = error

        mutate_task(self.task_id, _update)
        event_level = "error" if status == TASK_STATUS_FAILED else ("warning" if status in {TASK_STATUS_INTERRUPTED, TASK_STATUS_CANCELLED} else "info")
        self.log(
            f"Task finished: {status}",
            level=event_level,
            event_type="state",
            detail={"status": status, "error": error},
        )


def _auto_push_any2api(task_logger: TaskLogger, account) -> None:
    """Automatically push account to Any2API after successful registration (if configured)."""
    try:
        from core.any2api_sync import push_account_to_any2api
        push_account_to_any2api(account, log_fn=task_logger.log)
    except Exception as exc:
        task_logger.log(f"  [Any2API] Auto-push failed: {exc}", level="warning")


def _auto_upload_cpa(task_logger: TaskLogger, account) -> None:
    if getattr(account, "platform", "") != "chatgpt":
        return
    try:
        from core.config_store import config_store

        cpa_url = config_store.get("cpa_api_url", "")
        if cpa_url:
            from platforms.chatgpt.cpa_upload import generate_token_json, upload_to_cpa

            class _AccountProxy:
                pass

            target = _AccountProxy()
            target.email = account.email
            extra = account.extra or {}
            target.access_token = extra.get("access_token") or account.token
            target.refresh_token = extra.get("refresh_token", "")
            target.id_token = extra.get("id_token", "")
            target.session_token = extra.get("session_token", "")
            target.user_id = account.user_id or ""
            target.account_id = account.user_id or ""
            target.cookies = extra.get("cookies", "")

            token_data = generate_token_json(target)
            ok, msg = upload_to_cpa(token_data)
            task_logger.log(f"  [CPA] {'✓ ' + msg if ok else '✗ ' + msg}")
    except Exception as exc:
        task_logger.log(f"  [CPA] Auto-upload failed: {exc}", level="warning")


def _build_platform_instance(platform_name: str, payload: dict[str, Any], logger: TaskLogger, resolved_proxy: str | None = None, shared_mailbox=None):
    from core.base_identity import normalize_identity_provider
    from core.mailbox.registry import create_mailbox

    executor_type = str(payload.get("executor_type", "protocol") or "protocol")
    captcha_solver = str(payload.get("captcha_solver", "auto") or "auto")
    extra = dict(payload.get("extra") or {})
    config = RegisterConfig(
        executor_type=executor_type,
        captcha_solver=captcha_solver,
        proxy=resolved_proxy,
        extra=extra,
    )
    identity_provider = normalize_identity_provider(
        extra.get("identity_provider") or extra.get("identity_mode") or "mailbox"
    )
    extra["identity_provider"] = identity_provider
    mailbox = shared_mailbox
    if mailbox is None and identity_provider == "mailbox":
        if not extra.get("mail_provider"):
            from infrastructure.provider_settings_repository import ProviderSettingsRepository

            extra["mail_provider"] = ProviderSettingsRepository().get_default_provider_key("mailbox")
        mailbox = create_mailbox(
            provider=extra.get("mail_provider", ""),
            extra=extra,
            proxy=resolved_proxy,
        )

    platform_cls = get(platform_name)
    platform = platform_cls(config=config, mailbox=mailbox)
    if hasattr(platform, "set_logger"):
        platform.set_logger(logger.log)
    else:
        platform._log_fn = logger.log
    return platform


def _make_executor(max_workers: int = 1) -> ThreadPoolExecutor:
    return ThreadPoolExecutor(max_workers=max_workers)


def _run_single_account_check(account_id: int, logger: TaskLogger | None = None) -> tuple[bool, dict[str, Any]]:
    with Session(engine) as session:
        model = session.get(AccountModel, account_id)
        if not model:
            raise ValueError("Account does not exist")
        plugin = get(model.platform)(config=RegisterConfig())
        account = build_platform_account(session, model)

    valid = plugin.check_valid(account)
    with Session(engine) as session:
        model = session.get(AccountModel, account_id)
        if model:
            model.updated_at = _utcnow()
            current_graph = load_account_graphs(session, [account_id]).get(account_id, {})
            summary_updates = {"checked_at": _utcnow_iso(), "valid": bool(valid)}
            if hasattr(plugin, "get_last_check_overview"):
                summary_updates.update(plugin.get_last_check_overview() or {})
            lifecycle_status = None
            if valid:
                lifecycle_status = recover_lifecycle_status_for_valid_account(current_graph)
            patch_account_graph(
                session,
                model,
                lifecycle_status=lifecycle_status,
                summary_updates=summary_updates,
            )
            session.add(model)
            session.commit()

    result = {"account_id": account_id, "valid": bool(valid), "platform": account.platform, "email": account.email}
    if logger:
        logger.log(f"{account.email}: {'Valid' if valid else 'Invalid'}")
    return valid, result


def _auto_followup_windsurf_payment(
    *,
    platform_name: str,
    payload: dict[str, Any],
    platform,
    account,
    logger: "TaskLogger",
) -> None:
    if platform_name != "windsurf":
        return
    executor_type = str(payload.get("executor_type", "") or "").strip()
    use_browser = executor_type in {"headless", "headed"}
    if not use_browser:
        extra_cfg = dict(payload.get("extra") or {})
        if not _bool_config(extra_cfg.get("auto_payment_link"), True):
            return
    if not str(getattr(account, "password", "") or "").strip() and use_browser:
        logger.log("Windsurf post-registration auto-upgrade skipped: account missing password", level="error")
        return
    extra = dict(payload.get("extra") or {})
    turnstile_token = str(extra.get("turnstile_token") or "").strip()
    if use_browser:
        action_id = "payment_link_browser"
        params = {
            "timeout": _int_config(extra.get("windsurf_payment_timeout"), 240),
            "headless": "true" if _bool_config(extra.get("windsurf_payment_headless"), False) else "false",
            "payment_channel": "checkout",
        }
        if turnstile_token:
            params["turnstile_token"] = turnstile_token
    else:
        action_id = "payment_link"
        params = {}
        if turnstile_token:
            params["turnstile_token"] = turnstile_token
    logger.log("Registration successful, starting auto-generation of Windsurf Pro Trial Stripe link")
    try:
        result = platform.execute_action(action_id, account, params)
    except Exception as exc:
        message = f"Windsurf post-registration auto-upgrade failed: {exc}"
        logger.record_error(message)
        logger.log(message, level="error")
        return
    if not result.get("ok"):
        message = f"Windsurf post-registration auto-upgrade failed: {result.get('error') or 'unknown error'}"
        logger.record_error(message)
        logger.log(message, level="error")
        return
    data = dict(result.get("data") or {})
    if data:
        merged_extra = dict(getattr(account, "extra", {}) or {})
        merged_extra.update(data)
        account.extra = merged_extra
        save_account(account)
    cashier_url = str(data.get("cashier_url") or data.get("url") or "").strip()
    if cashier_url:
        logger.log(f"Windsurf auto-upgrade link generated: {cashier_url}")
        logger.add_cashier_url(cashier_url)


def _execute_register_task(payload: dict[str, Any], logger: TaskLogger) -> None:
    from core.proxy_pool import proxy_pool

    count = max(int(payload.get("count", 1) or 1), 1)
    concurrency = min(max(int(payload.get("concurrency", 1) or 1), 1), count, 5)
    platform_name = str(payload.get("platform", ""))
    email = payload.get("email") or None
    password = payload.get("password") or None
    proxy = payload.get("proxy") or None
    extra = dict(payload.get("extra") or {})
    sms_provider_key, sms_settings = _resolve_sms_provider_for_task(extra)
    herosms_enabled = sms_provider_key == "herosms" and bool(str(sms_settings.get("herosms_api_key") or "").strip())
    hero_extra_max = max(_int_config(sms_settings.get("register_phone_extra_max"), 3), 0) if herosms_enabled else 0
    hero_reuse_to_max = _bool_config(sms_settings.get("register_reuse_phone_to_max"), True) if herosms_enabled else False
    target_success = count
    max_success = count + hero_extra_max if herosms_enabled and hero_reuse_to_max else count
    progress_total = max_success if herosms_enabled else count

    logger.set_progress(0, progress_total)
    if herosms_enabled:
        logger.log(
            f"HeroSMS mode: target success {target_success}, auto-retry on failure, "
            f"up to {hero_extra_max} extra successes when the number is still reusable"
        )

    try:
        get(platform_name)
    except Exception as exc:
        logger.log(f"Fatal error: {exc}", level="error")
        logger.finish(TASK_STATUS_FAILED, error=str(exc))
        return

    success = 0
    errors: list[str] = []

    # Pre-create a shared mailbox instance for the entire task to avoid
    # concurrent initialization issues (e.g. MoeMail auto-registering
    # multiple provider accounts simultaneously).
    shared_mailbox = None
    try:
        from core.base_identity import normalize_identity_provider
        from core.mailbox.registry import create_mailbox

        identity_provider = normalize_identity_provider(
            extra.get("identity_provider") or extra.get("identity_mode") or "mailbox"
        )
        extra["identity_provider"] = identity_provider
        if identity_provider == "mailbox":
            if not extra.get("mail_provider"):
                from infrastructure.provider_settings_repository import ProviderSettingsRepository
                extra["mail_provider"] = ProviderSettingsRepository().get_default_provider_key("mailbox")
            shared_mailbox = create_mailbox(
                provider=extra.get("mail_provider", ""),
                extra=extra,
                proxy=proxy or None,
            )
    except Exception as exc:
        logger.log(f"Mailbox initialization failed: {exc}", level="error")
        logger.finish(TASK_STATUS_FAILED, error=f"Mailbox initialization failed: {exc}")
        return

    def _do_one(index: int) -> bool | str:
        if logger.is_cancel_requested():
            return "__cancel_requested__"
        resolved_proxy = proxy or proxy_pool.get_next()
        platform = _build_platform_instance(platform_name, payload, logger, resolved_proxy=resolved_proxy, shared_mailbox=shared_mailbox)
        try:
            logger.log(f"Starting registration of account {index + 1}/{count}")
            if resolved_proxy:
                logger.log(f"Using proxy: {resolved_proxy}")
            account = platform.register(email=email, password=password)
            save_account(account)
            _auto_followup_windsurf_payment(
                platform_name=platform_name,
                payload=payload,
                platform=platform,
                account=account,
                logger=logger,
            )
            if resolved_proxy:
                proxy_pool.report_success(resolved_proxy)
            logger.record_success()
            logger.log(f"✓ Registration successful: {account.email}")
            save_task_log(platform_name, account.email, "success")
            _auto_upload_cpa(logger, account)
            _auto_push_any2api(logger, account)
            extra = dict(account.extra or {})
            overview = dict(extra.get("account_overview") or {})
            cashier_url = str(extra.get("cashier_url") or overview.get("cashier_url") or "")
            if cashier_url:
                logger.log(f"  [Upgrade link] {cashier_url}")
                logger.add_cashier_url(cashier_url)
            return True
        except Exception as exc:
            if resolved_proxy:
                proxy_pool.report_fail(resolved_proxy)
            error = str(exc)
            logger.record_error(error)
            logger.log(f"✗ Registration failed: {error}", level="error")
            save_task_log(platform_name, email or "", "failed", error=error)
            return error

    try:
        submitted = 0
        completed = 0
        futures: dict[Any, int] = {}
        max_attempts = max(count if not herosms_enabled else max_success * 3, 1)

        def _hero_phone_alive() -> bool:
            if not (herosms_enabled and hero_reuse_to_max):
                return False
            try:
                from core.base_sms import is_herosms_phone_cache_alive
                alive, info = is_herosms_phone_cache_alive(sms_settings)
                if alive:
                    logger.log(
                        "HeroSMS number is still reusable: "
                        f"{str(info.get('phone_number') or '')[:5]}**** "
                        f"remaining {int(info.get('remaining_seconds') or 0)} seconds, "
                        f"successfully used {int(info.get('use_count') or 0)} times"
                    )
                return bool(alive)
            except Exception:
                return False

        def _should_submit_more() -> bool:
            if submitted >= max_attempts or logger.is_cancel_requested():
                return False
            if not herosms_enabled:
                return submitted < count
            if success + len(futures) >= max_success:
                return False
            if success < target_success:
                return True
            if success >= max_success:
                return False
            return _hero_phone_alive()

        with _make_executor(max_workers=concurrency) as pool:
            while _should_submit_more() and len(futures) < concurrency:
                futures[pool.submit(_do_one, submitted)] = submitted
                submitted += 1

            while futures:
                done, _ = wait(set(futures.keys()), return_when=FIRST_COMPLETED)
                for future in done:
                    futures.pop(future, None)
                    result = future.result()
                    completed += 1
                    if result is True:
                        success += 1
                    elif result != "__cancel_requested__":
                        errors.append(str(result))
                    logger.set_progress(min(success if herosms_enabled else completed, progress_total), progress_total)
                while _should_submit_more() and len(futures) < concurrency:
                    futures[pool.submit(_do_one, submitted)] = submitted
                    submitted += 1
                if logger.is_cancel_requested() and not futures:
                    break
    except Exception as exc:
        logger.log(f"Fatal error: {exc}", level="error")
        logger.finish(TASK_STATUS_FAILED, error=str(exc))
        return

    if herosms_enabled:
        logger.set_result_data({
            "target_count": target_success,
            "attempts": submitted,
            "success": success,
            "fail": len(errors),
            "extra_success": max(0, success - target_success),
            "hero_sms_reuse": True,
        })
    summary = f"Completed: {success} succeeded, {len(errors)} failed"
    logger.log(summary, event_type="summary")
    if logger.is_cancel_requested():
        logger.finish(TASK_STATUS_CANCELLED, error="Task cancelled")
        return
    final_status = TASK_STATUS_FAILED if errors and success == 0 else TASK_STATUS_SUCCEEDED
    final_error = "" if final_status == TASK_STATUS_SUCCEEDED else errors[0]
    logger.finish(final_status, error=final_error)


def _execute_platform_action_task(payload: dict[str, Any], logger: TaskLogger) -> None:
    command_platform = str(payload.get("platform", ""))
    account_id = int(payload.get("account_id", 0) or 0)
    action_id = str(payload.get("action_id", ""))
    params = dict(payload.get("params") or {})
    runtime = PlatformRuntime()
    result = runtime.execute_action(
        type("Command", (), {
            "platform": command_platform,
            "account_id": account_id,
            "action_id": action_id,
            "params": params,
        })()
    )
    if not result.ok:
        logger.record_error(result.error)
        logger.finish(TASK_STATUS_FAILED, error=result.error)
        return
    logger.set_result_data(result.data)
    message = ""
    if isinstance(result.data, dict):
        message = str(result.data.get("message", "") or "")
    if message:
        logger.log(message, event_type="summary")
    logger.set_progress(1, 1)
    logger.finish(TASK_STATUS_SUCCEEDED)


def _execute_account_check_task(payload: dict[str, Any], logger: TaskLogger) -> None:
    account_id = int(payload.get("account_id", 0) or 0)
    if account_id <= 0:
        logger.finish(TASK_STATUS_FAILED, error="Missing account_id")
        return
    try:
        _, result = _run_single_account_check(account_id, logger)
        logger.set_result_data(result)
        logger.set_progress(1, 1)
        logger.finish(TASK_STATUS_SUCCEEDED)
    except Exception as exc:
        logger.record_error(str(exc))
        logger.finish(TASK_STATUS_FAILED, error=str(exc))


def _execute_account_check_all_task(payload: dict[str, Any], logger: TaskLogger) -> None:
    platform = str(payload.get("platform", "") or "")
    limit = max(int(payload.get("limit", 50) or 50), 1)

    with Session(engine) as session:
        q = select(AccountModel)
        if platform:
            q = q.where(AccountModel.platform == platform)
        q = q.order_by(AccountModel.created_at.desc(), AccountModel.id.desc())
        accounts = session.exec(q.limit(limit)).all()

    total = len(accounts)
    logger.set_progress(0, total)
    if total == 0:
        logger.set_result_data({"valid": 0, "invalid": 0, "error": 0})
        logger.finish(TASK_STATUS_SUCCEEDED)
        return

    results = {"valid": 0, "invalid": 0, "error": 0}
    completed = 0
    for model in accounts:
        if logger.is_cancel_requested():
            logger.finish(TASK_STATUS_CANCELLED, error="Task cancelled")
            return
        try:
            valid, _ = _run_single_account_check(int(model.id or 0), logger)
            if valid:
                results["valid"] += 1
            else:
                results["invalid"] += 1
        except Exception as exc:
            results["error"] += 1
            logger.record_error(str(exc))
            logger.log(f"{model.email}: check exception {exc}", level="error")
        completed += 1
        logger.set_progress(completed, total)
    logger.set_result_data(results)
    logger.finish(TASK_STATUS_SUCCEEDED)


def execute_task(task_id: str) -> None:
    with Session(engine) as session:
        task = session.get(TaskModel, task_id)
        if not task:
            return
        task_type = task.type
        payload = task.get_payload()

    logger = TaskLogger(task_id)
    logger.mark_running()

    if logger.is_cancel_requested():
        logger.finish(TASK_STATUS_CANCELLED, error="Task cancelled immediately after startup")
        return

    handlers: dict[str, Callable[[dict[str, Any], TaskLogger], None]] = {
        TASK_TYPE_REGISTER: _execute_register_task,
        TASK_TYPE_ACCOUNT_CHECK: _execute_account_check_task,
        TASK_TYPE_ACCOUNT_CHECK_ALL: _execute_account_check_all_task,
        TASK_TYPE_PLATFORM_ACTION: _execute_platform_action_task,
    }
    handler = handlers.get(task_type)
    if not handler:
        logger.finish(TASK_STATUS_FAILED, error=f"Unknown task type: {task_type}")
        return
    handler(payload, logger)
