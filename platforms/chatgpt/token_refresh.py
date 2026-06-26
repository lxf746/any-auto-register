"""
Token refresh module
Supports two refresh methods: Session Token and OAuth Refresh Token
"""

import logging
import json
import time
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from curl_cffi import requests as cffi_requests

# from ..config.settings import get_settings  # removed: external dep
# from ..database.session import get_db  # removed: external dep
# from ..database import crud  # removed: external dep
# from ..database.models import Account  # removed: external dep

from core.datetime_utils import _utcnow

logger = logging.getLogger(__name__)


@dataclass
class TokenRefreshResult:
    """Token refresh result"""
    success: bool
    access_token: str = ""
    refresh_token: str = ""
    expires_at: Optional[datetime] = None
    error_message: str = ""


class TokenRefreshManager:
    """
    Token refresh manager
    Supports two refresh methods:
    1. Session Token refresh (priority)
    2. OAuth Refresh Token refresh
    """

    # OpenAI OAuth endpoints
    SESSION_URL = "https://chatgpt.com/api/auth/session"
    TOKEN_URL = "https://auth.openai.com/oauth/token"

    def __init__(self, proxy_url: Optional[str] = None):
        """
        Initialize Token refresh manager

        Args:
            proxy_url: Proxy URL
        """
        self.proxy_url = proxy_url
        from .constants import OAUTH_CLIENT_ID, OAUTH_REDIRECT_URI
        self._oauth_client_id = OAUTH_CLIENT_ID
        self._oauth_redirect_uri = OAUTH_REDIRECT_URI

    def _create_session(self) -> cffi_requests.Session:
        """Create HTTP session"""
        session = cffi_requests.Session(impersonate="chrome120", proxy=self.proxy_url)
        return session

    def refresh_by_session_token(self, session_token: str) -> TokenRefreshResult:
        """
        Refresh using Session Token

        Args:
            session_token: Session token

        Returns:
            TokenRefreshResult: Refresh result
        """
        result = TokenRefreshResult(success=False)

        try:
            session = self._create_session()

            # Set session Cookie
            session.cookies.set(
                "__Secure-next-auth.session-token",
                session_token,
                domain=".chatgpt.com",
                path="/"
            )

            # Request session endpoint
            response = session.get(
                self.SESSION_URL,
                headers={
                    "accept": "application/json",
                    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                },
                timeout=30
            )

            if response.status_code != 200:
                result.error_message = f"Session token refresh failed: HTTP {response.status_code}"
                logger.warning(result.error_message)
                return result

            data = response.json()

            # Extract access_token
            access_token = data.get("accessToken")
            if not access_token:
                result.error_message = "Session token refresh failed: accessToken not found"
                logger.warning(result.error_message)
                return result

            # Extract expiration time
            expires_at = None
            expires_str = data.get("expires")
            if expires_str:
                try:
                    expires_at = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
                except:
                    pass

            result.success = True
            result.access_token = access_token
            result.expires_at = expires_at

            logger.info(f"Session token refresh successful, expiration: {expires_at}")
            return result

        except Exception as e:
            result.error_message = f"Session token refresh exception: {str(e)}"
            logger.error(result.error_message)
            return result

    def refresh_by_oauth_token(
        self,
        refresh_token: str,
        client_id: Optional[str] = None
    ) -> TokenRefreshResult:
        """
        Refresh using OAuth Refresh Token

        Args:
            refresh_token: OAuth refresh token
            client_id: OAuth Client ID

        Returns:
            TokenRefreshResult: Refresh result
        """
        result = TokenRefreshResult(success=False)

        try:
            session = self._create_session()

            # Use configured client_id or default
            client_id = client_id or self._oauth_client_id

            # Build request body
            token_data = {
                "client_id": client_id,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "redirect_uri": self._oauth_redirect_uri
            }

            response = session.post(
                self.TOKEN_URL,
                headers={
                    "content-type": "application/x-www-form-urlencoded",
                    "accept": "application/json"
                },
                data=token_data,
                timeout=30
            )

            if response.status_code != 200:
                result.error_message = f"OAuth token refresh failed: HTTP {response.status_code}"
                logger.warning(f"{result.error_message}, response: {response.text[:200]}")
                return result

            data = response.json()

            # Extract tokens
            access_token = data.get("access_token")
            new_refresh_token = data.get("refresh_token", refresh_token)
            expires_in = data.get("expires_in", 3600)

            if not access_token:
                result.error_message = "OAuth token refresh failed: access_token not found"
                logger.warning(result.error_message)
                return result

            # Calculate expiration time
            expires_at = _utcnow() + timedelta(seconds=expires_in)

            result.success = True
            result.access_token = access_token
            result.refresh_token = new_refresh_token
            result.expires_at = expires_at

            logger.info(f"OAuth token refresh successful, expiration: {expires_at}")
            return result

        except Exception as e:
            result.error_message = f"OAuth token refresh exception: {str(e)}"
            logger.error(result.error_message)
            return result

    def refresh_account(self, account: Account) -> TokenRefreshResult:
        """
        Refresh account token

        Priority:
        1. Session Token refresh
        2. OAuth Refresh Token refresh

        Args:
            account: Account object

        Returns:
            TokenRefreshResult: Refresh result
        """
        # Try Session Token first
        if account.session_token:
            logger.info(f"Trying to refresh account {account.email} using Session Token")
            result = self.refresh_by_session_token(account.session_token)
            if result.success:
                return result
            logger.warning(f"Session Token refresh failed, trying OAuth refresh")

        # Try OAuth Refresh Token
        if account.refresh_token:
            logger.info(f"Trying to refresh account {account.email} using OAuth Refresh Token")
            result = self.refresh_by_oauth_token(
                refresh_token=account.refresh_token,
                client_id=account.client_id
            )
            return result

        # No available refresh method
        return TokenRefreshResult(
            success=False,
            error_message="Account has no available refresh method (missing session_token and refresh_token)"
        )

    def validate_token(self, access_token: str) -> Tuple[bool, Optional[str]]:
        """
        Validate whether Access Token is valid

        Args:
            access_token: Access token

        Returns:
            Tuple[bool, Optional[str]]: (whether valid, error message)
        """
        try:
            session = self._create_session()

            # Call OpenAI API to validate token
            response = session.get(
                "https://chatgpt.com/backend-api/me",
                headers={
                    "authorization": f"Bearer {access_token}",
                    "accept": "application/json"
                },
                timeout=30
            )

            if response.status_code == 200:
                return True, None
            elif response.status_code == 401:
                return False, "Token invalid or expired"
            elif response.status_code == 403:
                return False, "Account may be banned"
            else:
                return False, f"Validation failed: HTTP {response.status_code}"

        except Exception as e:
            return False, f"Validation exception: {str(e)}"


def refresh_account_token(account_id: int, proxy_url: Optional[str] = None) -> TokenRefreshResult:
    """
    Refresh specified account token and update database

    Args:
        account_id: Account ID
        proxy_url: Proxy URL

    Returns:
        TokenRefreshResult: Refresh result
    """
    with get_db() as db:
        account = crud.get_account_by_id(db, account_id)
        if not account:
            return TokenRefreshResult(success=False, error_message="Account does not exist")

        manager = TokenRefreshManager(proxy_url=proxy_url)
        result = manager.refresh_account(account)

        if result.success:
            # Update database
            update_data = {
                "access_token": result.access_token,
                "last_refresh": _utcnow()
            }

            if result.refresh_token:
                update_data["refresh_token"] = result.refresh_token

            if result.expires_at:
                update_data["expires_at"] = result.expires_at

            crud.update_account(db, account_id, **update_data)

        return result


def validate_account_token(account_id: int, proxy_url: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """
    Validate whether specified account's Token is valid

    Args:
        account_id: Account ID
        proxy_url: Proxy URL

    Returns:
        Tuple[bool, Optional[str]]: (whether valid, error message)
    """
    with get_db() as db:
        account = crud.get_account_by_id(db, account_id)
        if not account:
            return False, "Account does not exist"

        if not account.access_token:
            return False, "Account has no access_token"

        manager = TokenRefreshManager(proxy_url=proxy_url)
        return manager.validate_token(account.access_token)
