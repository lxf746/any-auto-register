"""Turnstile Solver 进程管理 - 后端启动时自动拉起"""
import subprocess
import sys
import os
import time
import threading
from typing import Optional
import requests

SOLVER_PORT = 8889
SOLVER_URL = f"http://localhost:{SOLVER_PORT}"
_proc: Optional[subprocess.Popen[bytes]] = None
_lock = threading.Lock()


def _browser_types() -> list[str]:
    configured = os.environ.get("SOLVER_BROWSER_TYPE", "camoufox,chromium")
    return [item.strip() for item in configured.split(",") if item.strip()]


def is_running() -> bool:
    try:
        r = requests.get(f"{SOLVER_URL}/", timeout=2)
        return r.status_code < 500
    except Exception:
        return False


def start():
    global _proc
    with _lock:
        if is_running():
            print("[Solver] 已在运行")
            return
        solver_script = os.path.join(
            os.path.dirname(__file__), "turnstile_solver", "start.py"
        )
        for browser_type in _browser_types():
            print(f"[Solver] 尝试启动 browser_type={browser_type}")
            _proc = subprocess.Popen(
                [sys.executable, solver_script, "--browser_type", browser_type],
            )

            for _ in range(30):
                time.sleep(1)
                if is_running():
                    print(f"[Solver] 已启动 PID={_proc.pid} browser_type={browser_type}")
                    return
                if _proc.poll() is not None:
                    print(f"[Solver] 启动失败 browser_type={browser_type} exit={_proc.returncode}")
                    break

            if _proc.poll() is None:
                _proc.terminate()
                _proc.wait(timeout=5)
                _proc = None

        print("[Solver] 所有浏览器方案均启动失败")


def stop():
    global _proc
    with _lock:
        if _proc and _proc.poll() is None:
            _proc.terminate()
            _proc.wait(timeout=5)
            print("[Solver] 已停止")
            _proc = None


def start_async():
    """在后台线程启动，不阻塞主进程"""
    t = threading.Thread(target=start, daemon=True)
    t.start()
