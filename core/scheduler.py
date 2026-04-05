"""定时任务调度 - 账号有效性检测、trial 到期提醒"""
from datetime import datetime, timezone

from sqlmodel import Session, select

from .account_graph import load_account_graphs, next_lifecycle_status_after_validity_check, patch_account_graph
from .base_platform import AccountStatus, RegisterConfig
from .db import engine, AccountModel
from .platform_accounts import build_platform_account
from .registry import get, load_all
import threading
import time


class Scheduler:
    def __init__(self):
        self._running = False
        self._thread: threading.Thread = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print("[Scheduler] 已启动")

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            try:
                self.check_trial_expiry()
            except Exception as e:
                print(f"[Scheduler] 错误: {e}")
            # 每小时检查一次
            time.sleep(3600)

    def check_trial_expiry(self):
        """检查 trial 到期账号，更新状态"""
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
                print(f"[Scheduler] {updated} 个 trial 账号已到期")

    def check_accounts_valid(self, platform: str = None, limit: int = 50):
        """批量检测账号有效性"""
        load_all()
        with Session(engine) as s:
            q = select(AccountModel)
            if platform:
                q = q.where(AccountModel.platform == platform)
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
                        next_status = next_lifecycle_status_after_validity_check(
                            getattr(getattr(account_obj, "status", None), "value", getattr(account_obj, "status", "")),
                            valid=bool(valid),
                        )
                        patch_account_graph(s, a, lifecycle_status=next_status)
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
