from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

from core.base_captcha import BaseCaptcha
from core.base_executor import BaseExecutor
from core.base_identity import IdentityMaterial

if TYPE_CHECKING:
    from core.base_platform import AccountStatus, BasePlatform, RegisterConfig


@dataclass(slots=True)
class RegistrationCapability:
    oauth_allowed_executor_types: tuple[str, ...] | None = None
    oauth_headless_requires_browser_reuse: bool = False
    browser_mailbox_requires_email: bool = True
    browser_mailbox_requires_mailbox: bool = True
    protocol_mailbox_requires_email: bool = True
    protocol_mailbox_requires_mailbox: bool = True


@dataclass(slots=True)
class RegistrationContext:
    platform_name: str
    platform_display_name: str
    platform: BasePlatform
    identity: IdentityMaterial
    config: RegisterConfig
    email: str | None
    password: str | None
    log_fn: Callable[[str], None]

    @property
    def executor_type(self) -> str:
        return str(getattr(self.config, "executor_type", "") or "protocol")

    @property
    def proxy(self) -> str | None:
        return getattr(self.config, "proxy", None)

    @property
    def extra(self) -> dict[str, Any]:
        return dict(getattr(self.config, "extra", {}) or {})

    def log(self, message: str) -> None:
        self.log_fn(message)


@dataclass(slots=True)
class RegistrationArtifacts:
    otp_callback: Callable[[], str] | None = None
    verification_link_callback: Callable[[], str] | None = None
    phone_callback: Callable[[], str] | None = None
    phone_cleanup: Callable[[], None] | None = None
    captcha_solver: BaseCaptcha | None = None
    executor: BaseExecutor | None = None
    raw_result: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RegistrationResult:
    email: str
    password: str
    user_id: str = ""
    region: str = ""
    token: str = ""
    status: AccountStatus | None = None
    trial_end_time: int = 0
    extra: dict[str, Any] = field(default_factory=dict)
