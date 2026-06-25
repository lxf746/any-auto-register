"""Kiro protocol mailbox registration worker."""
from __future__ import annotations

from typing import Callable

from platforms.kiro.core import KiroRegister, _pwd, wait_for_otp
from platforms.kiro.switch import send_kiro_message, load_session_messages


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

        session_token = tokens.get("sessionToken", "")
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
                    "accessToken": tokens["accessToken"],
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
                "accessToken": tokens["accessToken"],
                "sessionToken": session_token,
                "csrfToken": tokens.get("csrfToken", ""),
                "userId": tokens.get("userId", ""),
            }

        self.client.log("🎉 Registration complete! (with accessToken, no sessionToken)")
        return {
            "email": email,
            "password": use_password,
            "name": name,
            "accessToken": tokens["accessToken"],
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
