from __future__ import annotations

from contextlib import nullcontext

from core.rate_limiter import check_platform_limit, rate_limit_metrics
from .adapters import BrowserRegistrationAdapter, ProtocolMailboxAdapter, ProtocolOAuthAdapter
from .helpers import (
    build_link_callback,
    build_otp_callback,
    build_phone_callbacks,
    ensure_identity_email,
    ensure_mailbox_identity,
    ensure_oauth_browser_reuse,
    ensure_oauth_executor_allowed,
)
from .models import RegistrationArtifacts, RegistrationContext, RegistrationResult


class BrowserRegistrationFlow:
    def __init__(self, adapter: BrowserRegistrationAdapter):
        self.adapter = adapter

    def run(self, ctx: RegistrationContext) -> RegistrationResult:
        if self.adapter.preflight:
            self.adapter.preflight(ctx)

        if not check_platform_limit(ctx.platform_name, metrics=rate_limit_metrics):
            raise RuntimeError(f"Rate limit exceeded for platform {ctx.platform_name}")

        if getattr(ctx.identity, "identity_provider", "") == "oauth_browser":
            capability = self.adapter.capability
            ensure_oauth_executor_allowed(
                ctx,
                capability.oauth_allowed_executor_types,
            )
            if capability.oauth_headless_requires_browser_reuse and ctx.executor_type == "headless":
                ensure_oauth_browser_reuse(
                    ctx,
                    f"{ctx.platform_display_name} headless OAuth requires chrome_user_data_dir or chrome_cdp_url to reuse a local logged-in browser session",
                )
            if self.adapter.oauth_runner:
                raw = self.adapter.oauth_runner(ctx)
                return self.adapter.result_mapper(ctx, raw)

        if self.adapter.capability.browser_mailbox_requires_email:
            ensure_identity_email(ctx, f"{ctx.platform_display_name} browser mode requires email address")
        if self.adapter.capability.browser_mailbox_requires_mailbox:
            ensure_mailbox_identity(ctx, f"{ctx.platform_display_name} browser mailbox registration requires mailbox provider")

        artifacts = RegistrationArtifacts()
        if self.adapter.use_captcha_for_mailbox and getattr(ctx.identity, "identity_provider", "") == "mailbox":
            artifacts.captcha_solver = ctx.platform._make_captcha()
        if self.adapter.otp_spec:
            artifacts.otp_callback = build_otp_callback(
                ctx,
                keyword=self.adapter.otp_spec.keyword,
                timeout=self.adapter.otp_spec.timeout,
                code_pattern=self.adapter.otp_spec.code_pattern,
                wait_message=self.adapter.otp_spec.wait_message,
                success_label=self.adapter.otp_spec.success_label,
            )
        if self.adapter.link_spec:
            artifacts.verification_link_callback = build_link_callback(
                ctx,
                keyword=self.adapter.link_spec.keyword,
                timeout=self.adapter.link_spec.timeout,
                wait_message=self.adapter.link_spec.wait_message,
                success_label=self.adapter.link_spec.success_label,
                preview_chars=self.adapter.link_spec.preview_chars,
            )
        artifacts.phone_callback, artifacts.phone_cleanup = build_phone_callbacks(ctx, service=ctx.platform_name)

        try:
            worker = self.adapter.browser_worker_builder(ctx, artifacts) if self.adapter.browser_worker_builder else None
            if worker is None or self.adapter.browser_register_runner is None:
                raise RuntimeError(f"{ctx.platform_display_name} browser registration adapter not implemented")
            raw = self.adapter.browser_register_runner(worker, ctx, artifacts)
            artifacts.raw_result = raw
            return self.adapter.result_mapper(ctx, raw)
        finally:
            if artifacts.phone_cleanup:
                artifacts.phone_cleanup()


class ProtocolMailboxFlow:
    def __init__(self, adapter: ProtocolMailboxAdapter):
        self.adapter = adapter

    def run(self, ctx: RegistrationContext) -> RegistrationResult:
        if self.adapter.preflight:
            self.adapter.preflight(ctx)

        if not check_platform_limit(ctx.platform_name, metrics=rate_limit_metrics):
            raise RuntimeError(f"Rate limit exceeded for platform {ctx.platform_name}")

        if self.adapter.capability.protocol_mailbox_requires_email:
            ensure_identity_email(ctx, f"{ctx.platform_display_name} registration flow requires mailbox provider, no email account currently obtained")
        if self.adapter.capability.protocol_mailbox_requires_mailbox:
            ensure_mailbox_identity(ctx, f"{ctx.platform_display_name} registration flow requires mailbox provider, no email account currently obtained")

        artifacts = RegistrationArtifacts()
        if self.adapter.use_captcha:
            artifacts.captcha_solver = ctx.platform._make_captcha()
        if self.adapter.otp_spec:
            artifacts.otp_callback = build_otp_callback(
                ctx,
                keyword=self.adapter.otp_spec.keyword,
                timeout=self.adapter.otp_spec.timeout,
                code_pattern=self.adapter.otp_spec.code_pattern,
                wait_message=self.adapter.otp_spec.wait_message,
                success_label=self.adapter.otp_spec.success_label,
            )
        if self.adapter.link_spec:
            artifacts.verification_link_callback = build_link_callback(
                ctx,
                keyword=self.adapter.link_spec.keyword,
                timeout=self.adapter.link_spec.timeout,
                wait_message=self.adapter.link_spec.wait_message,
                success_label=self.adapter.link_spec.success_label,
                preview_chars=self.adapter.link_spec.preview_chars,
            )

        executor_cm = ctx.platform._make_executor() if self.adapter.use_executor else nullcontext(None)
        with executor_cm as executor:
            artifacts.executor = executor
            worker = self.adapter.worker_builder(ctx, artifacts)
            raw = self.adapter.register_runner(worker, ctx, artifacts)
            artifacts.raw_result = raw
            return self.adapter.result_mapper(ctx, raw)


class ProtocolOAuthFlow:
    def __init__(self, adapter: ProtocolOAuthAdapter):
        self.adapter = adapter

    def run(self, ctx: RegistrationContext) -> RegistrationResult:
        if self.adapter.preflight:
            self.adapter.preflight(ctx)
        ensure_oauth_executor_allowed(
            ctx,
            self.adapter.capability.oauth_allowed_executor_types,
        )
        if self.adapter.capability.oauth_headless_requires_browser_reuse and ctx.executor_type == "headless":
            ensure_oauth_browser_reuse(
                ctx,
                f"{ctx.platform_display_name} headless OAuth requires chrome_user_data_dir or chrome_cdp_url to reuse a local logged-in browser session",
            )
        raw = self.adapter.oauth_runner(ctx)
        return self.adapter.result_mapper(ctx, raw)
