"""Identity provider abstraction."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from core.mailbox.models import MailboxAccount


IDENTITY_PROVIDER_ALIASES = {
    "": "mailbox",
    "email": "mailbox",
    "mail": "mailbox",
    "mailbox": "mailbox",
    "oauth": "oauth_browser",
    "oauth_browser": "oauth_browser",
    "oauth_manual": "oauth_browser",   # backward-compat
    "manual_oauth": "oauth_browser",   # backward-compat
}

OAUTH_PROVIDER_ALIASES = {
    "google": "google",
    "google-oauth2": "google",
    "github": "github",
    "linkedin": "linkedin",
    "linkedin-openid": "linkedin",
    "microsoft": "microsoft",
    "windowslive": "microsoft",
    "live": "microsoft",
    "apple": "apple",
    "x": "x",
    "twitter": "x",
    "builderid": "builderid",
    "builder-id": "builderid",
    "builder_id": "builderid",
    "builder id": "builderid",
    "awsbuilderid": "builderid",
    "aws builder id": "builderid",
}


def normalize_identity_provider(value: Optional[str]) -> str:
    return IDENTITY_PROVIDER_ALIASES.get((value or "").strip().lower(), (value or "").strip().lower() or "mailbox")


def normalize_oauth_provider(value: Optional[str]) -> str:
    raw = (value or "").strip().lower()
    return OAUTH_PROVIDER_ALIASES.get(raw, raw)


@dataclass
class IdentityMaterial:
    identity_provider: str = "mailbox"
    email: str = ""
    mailbox_account: MailboxAccount | None = None
    before_ids: set = field(default_factory=set)
    oauth_provider: str = ""
    chrome_user_data_dir: str = ""
    chrome_cdp_url: str = ""
    metadata: dict = field(default_factory=dict)

    @property
    def has_mailbox(self) -> bool:
        return self.mailbox_account is not None


class BaseIdentityProvider(ABC):
    identity_provider: str = "mailbox"

    def __init__(self, *, mailbox=None, extra: dict = None):
        self.mailbox = mailbox
        self.extra = extra or {}

    @abstractmethod
    def resolve(self, requested_email: Optional[str] = None) -> IdentityMaterial:
        ...


class MailboxIdentityProvider(BaseIdentityProvider):
    identity_provider = "mailbox"

    def resolve(self, requested_email: Optional[str] = None) -> IdentityMaterial:
        requested_email = (requested_email or "").strip()
        if not self.mailbox:
            return IdentityMaterial(identity_provider=self.identity_provider, email=requested_email)

        mail_acct = self.mailbox.get_email()
        email = getattr(mail_acct, "email", "") or ""
        if not requested_email and not email:
            provider_name = getattr(self.mailbox, "__class__", type(self.mailbox)).__name__
            raise ValueError(f"{provider_name} did not return a usable email, please check mailbox provider config or service status")
        if requested_email and email and requested_email != email:
            raise ValueError(f"Provided email {requested_email} does not match the email returned by current mailbox provider {email}")
        before_ids = self.mailbox.get_current_ids(mail_acct) if mail_acct else set()
        return IdentityMaterial(
            identity_provider=self.identity_provider,
            email=requested_email or email,
            mailbox_account=mail_acct,
            before_ids=before_ids,
        )


class BrowserOAuthIdentityProvider(BaseIdentityProvider):
    identity_provider = "oauth_browser"

    def resolve(self, requested_email: Optional[str] = None) -> IdentityMaterial:
        email = (requested_email or self.extra.get("oauth_email_hint", "") or "").strip()
        oauth_provider = normalize_oauth_provider(
            self.extra.get("oauth_provider") or self.extra.get("default_oauth_provider")
        )
        return IdentityMaterial(
            identity_provider=self.identity_provider,
            email=email,
            oauth_provider=oauth_provider,
            chrome_user_data_dir=self.extra.get("chrome_user_data_dir", ""),
            chrome_cdp_url=self.extra.get("chrome_cdp_url", ""),
            metadata={
                "oauth_email_hint": self.extra.get("oauth_email_hint", ""),
            },
        )


# Backward-compat alias
ManualOAuthIdentityProvider = BrowserOAuthIdentityProvider


def create_identity_provider(mode: Optional[str], *, mailbox=None, extra: dict = None) -> BaseIdentityProvider:
    normalized = normalize_identity_provider(mode)
    if normalized == "mailbox":
        return MailboxIdentityProvider(mailbox=mailbox, extra=extra)
    if normalized == "oauth_browser":
        return BrowserOAuthIdentityProvider(mailbox=mailbox, extra=extra)
    raise ValueError(f"Unknown identity_provider: {mode}")
