"""Scheduled task scheduler - account validity checks, trial expiry reminders"""
from datetime import datetime, timezone
import logging

from sqlmodel import Session, select

from .account_graph import load_account_graphs, patch_account_graph
from .base_platform import AccountStatus, RegisterConfig
from .db import engine, AccountModel
from core.datetime_utils import _utcnow_iso
from .platform_accounts import build_platform_account
from .registry import get, load_all
import threading
import time

logger = logging.getLogger(__name__)

# Scheduler poll interval (1 hour)
POLL_INTERVAL_SECONDS = 3600


class Scheduler:
    def __init__(self):
        self._running = False
        self._thread: threading.Thread = None
        self._stop_event = threading.Event()

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Started")

    def stop(self):
        self._running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)

    def _loop(self):
        while self._running:
            try:
                self.check_trial_expiry()
            except Exception as e:
                logger.error("Error: %s", e)
            # Check every hour
            self._stop_event.wait(POLL_INTERVAL_SECONDS)

    def check_trial_expiry(self):
        """Check trial expiry accounts and update status"""
        now = int(datetime.now(timezone.utc).timestamp())
        with Session(engine) as s:
            accounts = s.exec(select(AccountModel)).all()
            graphs = load_account_graphs(s, [int(acc.id or 0) for acc in accounts if acc.id])
            updated = 0
            for acc in accounts:
                graph = graphs.get(int(acc.id or 0), {})
                if graph.get("lifecycle_status") != "trial":
                    continue
                trial_end_time = int((graph.get("overview") or {}).get("trial_end_time") or 0)
                if trial_end_time and trial_end_time < now:
                    acc.updated_at = datetime.now(timezone.utc)
                    patch_account_graph(s, acc, lifecycle_status=AccountStatus.EXPIRED.value)
                    s.add(acc)
                    updated += 1
            s.commit()
            if updated:
                logger.info("%d trial accounts expired", updated)

    def check_accounts_valid(self, platform: str = None, limit: int = 50):
        """Batch check account validity"""
        load_all()
        with Session(engine) as s:
            q = select(AccountModel)
            if platform:
                q = q.where(AccountModel.platform == platform)
            q = q.order_by(AccountModel.created_at.desc(), AccountModel.id.desc())
            accounts = s.exec(q.limit(limit)).all()
            graphs = load_account_graphs(s, [int(acc.id or 0) for acc in accounts if acc.id])
            accounts = [
                acc for acc in accounts
                if graphs.get(int(acc.id or 0), {}).get("lifecycle_status") in {"registered", "trial", "subscribed"}
            ]

        results = {"valid": 0, "invalid": 0, "error": 0}
        for acc in accounts:
            try:
                PlatformCls = get(acc.platform)
                plugin = PlatformCls(config=RegisterConfig())
                with Session(engine) as s:
                    current = s.get(AccountModel, acc.id)
                    if not current:
                        continue
                    account_obj = build_platform_account(s, current)
                valid = plugin.check_valid(account_obj)
                with Session(engine) as s:
                    a = s.get(AccountModel, acc.id)
                    if a:
                        a.updated_at = datetime.now(timezone.utc)
                        summary_updates = {"checked_at": _utcnow_iso(), "valid": valid}
                        if hasattr(plugin, "get_last_check_overview"):
                            summary_updates.update(plugin.get_last_check_overview() or {})
                        patch_account_graph(
                            s,
                            a,
                            summary_updates=summary_updates,
                        )
                        s.add(a)
                        s.commit()
                if valid:
                    results["valid"] += 1
                else:
                    results["invalid"] += 1
            except Exception:
                results["error"] += 1
        return results


scheduler = Scheduler()
