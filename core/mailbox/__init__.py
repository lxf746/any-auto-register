"""Mailbox provider package — exports all providers and utilities."""
from core.mailbox.models import MailboxAccount
from core.mailbox.base import BaseMailbox, FallbackMailbox, ResilientMailbox
from core.mailbox.utils import extract_verification_link, normalize_api_base_url
from core.mailbox.config import (
    MailboxConfig,
    LaoudoConfig,
    AitreConfig,
    TempMailLolConfig,
    TempMailWebConfig,
    DuckMailConfig,
    CFWorkerConfig,
    MoeMailConfig,
    FreemailConfig,
    TestmailConfig,
    DDGEmailConfig,
    MailTmConfig,
    TempyEmailConfig,
)
from core.mailbox.resilience import (
    HealthCheck,
    HealthCheckConfig,
    CircuitBreaker,
    CircuitBreakerConfig,
    RateLimiter,
    RateLimiterConfig,
    EmailDedup,
    ResilienceConfig,
)
from core.mailbox.laoudo import LaoudoMailbox
from core.mailbox.aitre import AitreMailbox
from core.mailbox.tempmail_lol import TempMailLolMailbox
from core.mailbox.tempmail_web import TempMailWebMailbox
from core.mailbox.duckmail import DuckMailMailbox
from core.mailbox.cfworker import CFWorkerMailbox
from core.mailbox.moemail import MoeMailMailbox
from core.mailbox.freemail import FreemailMailbox
from core.mailbox.testmail import TestmailMailbox
from core.mailbox.ddg_email import DDGEmailMailbox

__all__ = [
    "MailboxAccount",
    "BaseMailbox",
    "FallbackMailbox",
    "ResilientMailbox",
    "extract_verification_link",
    "normalize_api_base_url",
    "MailboxConfig",
    "LaoudoConfig",
    "AitreConfig",
    "TempMailLolConfig",
    "TempMailWebConfig",
    "DuckMailConfig",
    "CFWorkerConfig",
    "MoeMailConfig",
    "FreemailConfig",
    "TestmailConfig",
    "DDGEmailConfig",
    "MailTmConfig",
    "TempyEmailConfig",
    "HealthCheck",
    "HealthCheckConfig",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "RateLimiter",
    "RateLimiterConfig",
    "EmailDedup",
    "ResilienceConfig",
    "LaoudoMailbox",
    "AitreMailbox",
    "TempMailLolMailbox",
    "TempMailWebMailbox",
    "DuckMailMailbox",
    "CFWorkerMailbox",
    "MoeMailMailbox",
    "FreemailMailbox",
    "TestmailMailbox",
    "DDGEmailMailbox",
]
