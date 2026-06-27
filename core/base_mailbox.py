"""Mailbox pool base class - abstract temporary mailbox / inbound service

DEPRECATED: Import from core.mailbox instead. This module re-exports for backward compatibility.
"""
from core.mailbox.models import MailboxAccount
from core.mailbox.base import BaseMailbox, FallbackMailbox
from core.mailbox.utils import extract_verification_link as _extract_verification_link
from core.mailbox.utils import normalize_api_base_url as _normalize_api_base_url
from core.mailbox.registry import create_mailbox

# Re-export provider classes for backward compatibility
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
from core.mailbox.mailtm import MailTmMailbox
from core.mailbox.tempyemail import TempyMailbox

# Re-export default URLs
from core.mailbox.laoudo import DEFAULT_LAOUDO_API_URL
from core.mailbox.aitre import DEFAULT_AITRE_API_URL
from core.mailbox.tempmail_lol import DEFAULT_TEMPMAIL_LOL_API_URL
from core.mailbox.tempmail_web import DEFAULT_TEMPMAIL_WEB_BASE_URL
from core.mailbox.mailtm import DEFAULT_MAILTM_API_URL
