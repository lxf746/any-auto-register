from __future__ import annotations

import time

from core.base_mailbox import MailboxAccount, OmniMailMailbox


class FakeResponse:
    def __init__(self, status_code: int, data: dict):
        self.status_code = status_code
        self._data = data
        self.ok = 200 <= status_code < 400
        self.text = str(data)

    def json(self):
        return self._data


class FakeSession:
    def __init__(self, *, posts: list[FakeResponse] | None = None,
                 requests: list[FakeResponse] | None = None):
        self.posts = list(posts or [])
        self.requests = list(requests or [])
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return self.posts.pop(0)

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.requests.pop(0)


def make_provider() -> OmniMailMailbox:
    OmniMailMailbox._token_cache.clear()
    return OmniMailMailbox(
        api_url="https://mail.example.com/",
        username="automation@example.com",
        password="secret",
        domain="inbox.example.com",
    )


def token_response(access: str = "om_at_access", refresh: str = "om_rt_refresh") -> FakeResponse:
    return FakeResponse(200, {"accessToken": access, "refreshToken": refresh})


def test_get_email_issues_token_and_creates_mailbox(monkeypatch):
    provider = make_provider()
    provider._session = FakeSession(
        posts=[token_response()],
        requests=[FakeResponse(201, {"mailbox": {"address": "abcdefghijkl@inbox.example.com"}})],
    )
    monkeypatch.setattr("random.choices", lambda *args, **kwargs: list("abcdefghijkl"))

    account = provider.get_email()

    assert account.email == "abcdefghijkl@inbox.example.com"
    assert account.account_id == account.email
    assert provider._session.calls[0][1].endswith("/api/auth/token")
    create_call = provider._session.calls[1]
    assert create_call[1].endswith("/api/mailboxes")
    assert create_call[2]["headers"]["authorization"] == "Bearer om_at_access"
    assert create_call[2]["json"] == {"address": account.email}


def test_request_refreshes_expired_access_token():
    provider = make_provider()
    provider._access_token = "om_at_old"
    provider._refresh_token = "om_rt_old"
    provider._session = FakeSession(
        posts=[token_response("om_at_new", "om_rt_new")],
        requests=[
            FakeResponse(401, {"error": "expired"}),
            FakeResponse(200, {"messages": [{"id": "message-1"}]}),
        ],
    )

    assert provider._get_mails("box@inbox.example.com") == [{"id": "message-1"}]
    assert provider._session.calls[1][1].endswith("/api/auth/token/refresh")
    assert provider._session.calls[2][2]["headers"]["authorization"] == "Bearer om_at_new"


def test_provider_instances_reuse_process_token_cache():
    provider = make_provider()
    provider._session = FakeSession(
        posts=[token_response()],
        requests=[FakeResponse(200, {"messages": []})],
    )
    provider._get_mails("box@inbox.example.com")

    second = OmniMailMailbox(
        api_url="https://mail.example.com",
        username="automation@example.com",
        password="secret",
        domain="inbox.example.com",
    )
    second._session = FakeSession(requests=[FakeResponse(200, {"messages": []})])

    assert second._get_mails("box@inbox.example.com") == []
    assert second._session.calls[0][2]["headers"]["authorization"] == "Bearer om_at_access"


def test_wait_for_code_retries_while_message_is_processing(monkeypatch):
    provider = make_provider()
    account = MailboxAccount(email="box@inbox.example.com")
    calls = 0

    def get_mails(_email):
        nonlocal calls
        calls += 1
        status = "processing" if calls == 1 else "ready"
        return [{"id": "message-1", "status": status}]

    monkeypatch.setattr(provider, "_get_mails", get_mails)
    monkeypatch.setattr(provider, "_message_text", lambda _mail: "Cursor verification code: 482913")
    monkeypatch.setattr(time, "sleep", lambda _seconds: None)

    assert provider.wait_for_code(account, keyword="cursor", timeout=1) == "482913"
    assert calls == 2


def test_wait_for_link_reads_message_detail(monkeypatch):
    provider = make_provider()
    account = MailboxAccount(email="box@inbox.example.com")
    monkeypatch.setattr(
        provider,
        "_get_mails",
        lambda _email: [{"id": "message-2", "status": "ready"}],
    )
    monkeypatch.setattr(
        provider,
        "_message_text",
        lambda _mail: "Tavily verification https://app.tavily.com/verify?token=abc",
    )

    assert provider.wait_for_link(account, keyword="tavily", timeout=1) == (
        "https://app.tavily.com/verify?token=abc"
    )


def test_provider_catalog_includes_omnimail():
    from infrastructure.provider_definitions_repository import ProviderDefinitionsRepository

    repository = ProviderDefinitionsRepository()
    repository.ensure_seeded()
    provider = repository.get_by_key("mailbox", "omnimail_api")

    assert provider is not None
    assert provider.label == "OmniMail（自建域名）"
    assert {field["key"] for field in provider.get_fields()} == {
        "omnimail_api_url",
        "omnimail_domain",
        "omnimail_username",
        "omnimail_password",
    }
