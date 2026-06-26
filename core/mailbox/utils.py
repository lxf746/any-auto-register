"""Shared mailbox utilities — verification link extraction, URL normalization."""
import html
import re
from urllib.parse import urlparse


def extract_verification_link(text: str, keyword: str = "") -> str | None:
    """Extract verification link from email text."""
    combined = str(text or "")
    lowered = combined.lower()
    if keyword and keyword.lower() not in lowered:
        return None

    urls = [
        html.unescape(raw).rstrip(").,;")
        for raw in re.findall(r'https?://[^\s<>"\']+', combined, re.IGNORECASE)
    ]
    if not urls:
        return None

    primary_link_hints = ("verif", "confirm", "magic", "auth", "callback", "signin", "signup", "continue")
    primary_host_hints = ("tavily", "firecrawl", "clerk", "stytch", "auth", "login")
    for url in urls:
        url_lower = url.lower()
        if any(token in url_lower for token in primary_link_hints) and any(host in url_lower for host in primary_host_hints):
            return url

    verification_hints = ("verify", "verification", "confirm", "magic link", "sign in", "login", "auth", "tavily", "firecrawl")
    if not any(token in lowered for token in verification_hints):
        return None

    for url in urls:
        url_lower = url.lower()
        if any(token in url_lower for token in primary_link_hints):
            return url

    return urls[0]


def normalize_api_base_url(value: str | None, *, default: str, label: str) -> str:
    """Normalize and validate an API base URL."""
    raw = str(value or "").strip() or default
    if "://" not in raw:
        raw = f"https://{raw.lstrip('/')}"
    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"{label} invalid: {value!r}")
    return raw.rstrip("/")
