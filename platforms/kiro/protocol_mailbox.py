"""Kiro protocol mailbox registration worker."""
from __future__ import annotations

import json
import os
import uuid
from typing import Callable

import requests as http_requests

from platforms.kiro.core import KiroRegister, _pwd, wait_for_otp
from platforms.kiro.switch import send_kiro_message, load_session_messages


def push_account_to_any2api(
    access_token: str,
    *,
    any2api_url: str = "",
    any2api_password: str = "",
    name: str = "",
    active: bool = True,
    machine_id: str = "",
    preferred_endpoint: str = "amazonq",
    log_fn: Callable[[str], None] = print,
) -> bool:
    """Push a registered Kiro account to any2api account pool.

    Args:
        access_token: The Kiro accessToken from ExchangeToken.
        any2api_url: Base URL of any2api server (e.g. http://192.168.1.100:8099).
            Falls back to ANY2API_URL env var.
        any2api_password: Admin password for any2api. Falls back to ANY2API_PASSWORD env var.
        name: Optional account name. Defaults to "Kiro Account <timestamp>".
        active: Whether to mark this account as active (default True).
        machine_id: Optional machine ID. Auto-generated as UUID if empty.
        preferred_endpoint: "amazonq" or "codewhisperer" (default "amazonq").
        log_fn: Logging function.

    Returns:
        True on success, False on failure.
    """
    base_url = (any2api_url or os.environ.get("ANY2API_URL", "")).rstrip("/")
    admin_pwd = any2api_password or os.environ.get("ANY2API_PASSWORD", "")
    if not base_url:
        log_fn("  ⚠️ ANY2API_URL not configured, skipping push")
        return False
    if not admin_pwd:
        log_fn("  ⚠️ ANY2API_PASSWORD not configured, skipping push")
        return False

    try:
        # 1. Login to get admin session token
        log_fn(f"  Pushing account to any2api at {base_url}...")
        login_r = http_requests.post(
            f"{base_url}/admin/api/auth/login",
            json={"password": admin_pwd},
            timeout=10,
        )
        if login_r.status_code != 200:
            log_fn(f"  ❌ any2api login failed: HTTP {login_r.status_code} {login_r.text[:200]}")
            return False
        session_token = login_r.json().get("token", "")
        if not session_token:
            log_fn("  ❌ any2api login returned no token")
            return False

        auth_headers = {"Authorization": f"Bearer {session_token}", "Content-Type": "application/json"}

        # 2. Add account
        account = {
            "accessToken": access_token,
            "active": active,
            "preferredEndpoint": preferred_endpoint,
            "machineId": machine_id or str(uuid.uuid4()),
            "name": name or f"Kiro Account {int(__import__('time').time())}",
        }
        create_r = http_requests.post(
            f"{base_url}/admin/api/providers/kiro/accounts/create",
            headers=auth_headers,
            json=account,
            timeout=10,
        )
        if create_r.status_code != 200:
            log_fn(f"  ❌ any2api create account failed: HTTP {create_r.status_code} {create_r.text[:200]}")
            return False

        log_fn(f"  ✅ Account pushed to any2api: {create_r.json().get('account', {}).get('id', '?')}")
        return True

    except Exception as e:
        log_fn(f"  ❌ any2api push exception: {e}")
        return False


class KiroProtocolMailboxWorker:
    def __init__(self, *, proxy: str | None = None, tag: str = "KIRO", log_fn: Callable[[str], None] = print):
        self.client = KiroRegister(proxy=proxy, tag=tag)
        self.client.log = lambda msg: log_fn(msg)
        self._tokens: dict = {}

    def run(
        self,
        *,
        email: str,
        password: str | None = None,
        name: str = "Kiro User",
        mail_token: str | None = None,
        otp_timeout: int = 120,
        otp_callback: Callable[[], str] | None = None,
        any2api_url: str = "",
        any2api_password: str = "",
    ) -> dict:
        use_password = password or _pwd()
        self.client.log(f"  Auto-generated password: {use_password}" if not password
                        else f"  Using provided password: {use_password}")
        self.client.log(f"========== Starting registration: {email} ==========")

        redir = self.client.step1_kiro_init()
        if not redir:
            raise RuntimeError("InitiateLogin failed")
        if not self.client.step2_get_wsh(redir):
            raise RuntimeError("Failed to get wsh")
        if not self.client.step3_signin_flow(email):
            raise RuntimeError("signin flow failed")
        if not self.client.step4_signup_flow(email):
            raise RuntimeError("signup flow failed")
        if not self.client._profile_wf_id:
            raise RuntimeError("Failed to get workflowID")

        tes = self.client.step5_get_tes_token()
        if not tes:
            self.client.log("  ⚠️ TES token fetch failed, continuing...")

        if not self.client.step6_profile_load():
            raise RuntimeError("profile start failed")
        if self.client.step7_send_otp(email) is None:
            raise RuntimeError("send OTP failed")

        if otp_callback:
            self.client.log("  Auto-fetching OTP...")
            otp = otp_callback()
        elif mail_token:
            self.client.log("  Auto-fetching OTP...")
            otp = wait_for_otp(mail_token, timeout=otp_timeout, tag=self.client.tag)
        else:
            otp = input(f"[{self.client.tag}] Please enter OTP: ").strip()
        if not otp:
            raise RuntimeError("Failed to get OTP")

        identity = self.client.step8_create_identity(otp, email, name)
        if not identity:
            raise RuntimeError("create-identity failed")
        reg_code = identity["registrationCode"]
        sign_in_state = identity["signInState"]

        signup_registration = self.client.step9_signup_registration(reg_code, sign_in_state)
        if not signup_registration:
            raise RuntimeError("signup registration failed")
        password_state = self.client.step10_set_password(use_password, email, signup_registration)
        if not password_state:
            raise RuntimeError("Password setup failed")

        login_result = self.client.step11_final_login(email, password_state)
        if not login_result:
            self.client.log("  ⚠️ Final login step failed, but account may have been created successfully")

        tokens = self.client.step12_get_tokens()
        if not tokens:
            self.client.log("🎉 Registration complete! (but token fetch failed, account is usable)")
            return {"email": email, "password": use_password, "name": name}

        self._tokens = {
            "accessToken": tokens.get("accessToken", ""),
            "sessionToken": tokens.get("sessionToken", ""),
            "csrfToken": tokens.get("csrfToken", ""),
            "userId": tokens.get("userId", ""),
        }

        access_token = tokens.get("accessToken", "")
        session_token = tokens.get("sessionToken", "")

        # Push to any2api if configured
        if access_token:
            push_account_to_any2api(
                access_token,
                any2api_url=any2api_url,
                any2api_password=any2api_password,
                name=f"Kiro {email}",
                log_fn=self.client.log,
            )

        if session_token:
            device_tokens = self.client.step12f_device_auth(session_token)
            if device_tokens:
                self.client.log("🎉 Registration complete! (with accessToken + sessionToken + refreshToken)")
                self._tokens.update({
                    "clientId": device_tokens["clientId"],
                    "clientSecret": device_tokens["clientSecret"],
                    "refreshToken": device_tokens["refreshToken"],
                })
                return {
                    "email": email,
                    "password": use_password,
                    "name": name,
                    "accessToken": access_token,
                    "sessionToken": session_token,
                    "csrfToken": tokens.get("csrfToken", ""),
                    "userId": tokens.get("userId", ""),
                    "clientId": device_tokens["clientId"],
                    "clientSecret": device_tokens["clientSecret"],
                    "refreshToken": device_tokens["refreshToken"],
                }

            self.client.log("🎉 Registration complete! (with accessToken + sessionToken, but refreshToken fetch failed)")
            return {
                "email": email,
                "password": use_password,
                "name": name,
                "accessToken": access_token,
                "sessionToken": session_token,
                "csrfToken": tokens.get("csrfToken", ""),
                "userId": tokens.get("userId", ""),
            }

        self.client.log("🎉 Registration complete! (with accessToken, no sessionToken)")
        return {
            "email": email,
            "password": use_password,
            "name": name,
            "accessToken": access_token,
        }

    def send_message(self, prompt: str, *, timeout: int = 120) -> str:
        """Send a prompt to Q Developer and return the full assistant response text.

        Requires a prior successful registration with sessionToken and userId.
        """
        if not self._tokens:
            raise RuntimeError("No tokens available. Call run() first.")
        return send_kiro_message(
            prompt,
            access_token=self._tokens.get("accessToken", ""),
            session_token=self._tokens.get("sessionToken", ""),
            user_id=self._tokens.get("userId", ""),
            csrf_token=self._tokens.get("csrfToken", ""),
            timeout=timeout,
        )

    def load_session(self, space_id: str, session_id: str, *, timeout: int = 30) -> list[dict]:
        """Load conversation history from a session.

        Requires a prior successful registration with sessionToken and userId.
        """
        if not self._tokens:
            raise RuntimeError("No tokens available. Call run() first.")
        return load_session_messages(
            space_id, session_id,
            access_token=self._tokens.get("accessToken", ""),
            session_token=self._tokens.get("sessionToken", ""),
            user_id=self._tokens.get("userId", ""),
            csrf_token=self._tokens.get("csrfToken", ""),
            timeout=timeout,
        )
