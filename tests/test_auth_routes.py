"""Integration tests for the JSON auth API, driven through the HTTP layer.

These exercise the full stack (``/api`` routes -> UserManager -> Postgres) with a
fake email sender that captures the verification / reset tokens the flows emit.
"""

from conftest import CapturingEmailSender, StubPwnedChecker
from httpx import AsyncClient, Response

VERIFY = "verify"
RESET = "reset"

EMAIL = "alice@example.com"
PASSWORD = "sup3r-secret-pw"
NEW_PASSWORD = "an0ther-secret-pw"

_CHECK_INBOX = "Account created. Check your inbox to confirm your email address."


async def _register(
    client: AsyncClient, email: str = EMAIL, password: str = PASSWORD
) -> None:
    response = await client.post(
        "/api/auth/register", json={"email": email, "password": password}
    )
    assert response.status_code == 202
    assert response.json() == {"message": _CHECK_INBOX}


async def _verify(client: AsyncClient, sender: CapturingEmailSender) -> None:
    token = sender.last_token(VERIFY)
    response = await client.post("/api/auth/verify", json={"token": token})
    assert response.status_code == 200


async def _login(
    client: AsyncClient, email: str = EMAIL, password: str = PASSWORD
) -> Response:
    # fastapi-users' login router uses the OAuth2 password form (``username``).
    return await client.post(
        "/api/auth/login", data={"username": email, "password": password}
    )


async def test_register_sends_verification_email(
    client: AsyncClient,
    email_sender: CapturingEmailSender,
) -> None:
    await _register(client)
    assert any(e.kind == VERIFY and e.email == EMAIL for e in email_sender.sent)


async def test_register_does_not_enumerate_existing_accounts(
    client: AsyncClient,
    email_sender: CapturingEmailSender,
) -> None:
    await _register(client)
    await _verify(client, email_sender)
    email_sender.sent.clear()
    # Registering the same address again must look identical to a fresh signup
    # (neutral 202, no error) and must not re-send a verification email.
    response = await client.post(
        "/api/auth/register", json={"email": EMAIL, "password": PASSWORD}
    )
    assert response.status_code == 202
    assert response.json() == {"message": _CHECK_INBOX}
    assert email_sender.sent == []


async def test_login_blocked_until_verified(
    client: AsyncClient,
    email_sender: CapturingEmailSender,
) -> None:
    await _register(client)
    response = await _login(client)
    assert response.status_code == 400
    assert response.json()["detail"] == "LOGIN_USER_NOT_VERIFIED"
    assert "set-cookie" not in response.headers
    # No verification email was sent by the login attempt itself.
    assert all(e.kind == VERIFY for e in email_sender.sent)


async def test_verify_then_login_sets_cookie(
    client: AsyncClient,
    email_sender: CapturingEmailSender,
) -> None:
    await _register(client)
    await _verify(client, email_sender)
    response = await _login(client)
    assert response.status_code == 204
    assert "papertrailauth" in response.headers.get("set-cookie", "")
    # The authenticated session now reaches the protected profile endpoint.
    me = await client.get("/api/users/me")
    assert me.status_code == 200
    assert me.json()["email"] == EMAIL


async def test_login_wrong_password_is_rejected(
    client: AsyncClient,
    email_sender: CapturingEmailSender,
) -> None:
    await _register(client)
    await _verify(client, email_sender)
    response = await _login(client, password="wrong-password")
    assert response.status_code == 400
    assert response.json()["detail"] == "LOGIN_BAD_CREDENTIALS"
    assert "set-cookie" not in response.headers


async def test_forgot_then_reset_password(
    client: AsyncClient,
    email_sender: CapturingEmailSender,
) -> None:
    await _register(client)
    await _verify(client, email_sender)
    forgot = await client.post("/api/auth/forgot-password", json={"email": EMAIL})
    assert forgot.status_code == 202
    token = email_sender.last_token(RESET)
    reset = await client.post(
        "/api/auth/reset-password", json={"token": token, "password": NEW_PASSWORD}
    )
    assert reset.status_code == 200
    # The new password now works and the old one does not.
    assert (await _login(client, password=NEW_PASSWORD)).status_code == 204
    bad = await _login(client, password=PASSWORD)
    assert bad.status_code == 400


async def test_reset_password_with_invalid_token(client: AsyncClient) -> None:
    response = await client.post(
        "/api/auth/reset-password",
        json={"token": "not-a-real-token", "password": NEW_PASSWORD},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "RESET_PASSWORD_BAD_TOKEN"


async def test_forgot_password_does_not_enumerate(
    client: AsyncClient,
    email_sender: CapturingEmailSender,
) -> None:
    response = await client.post(
        "/api/auth/forgot-password", json={"email": "nobody@example.com"}
    )
    # No account exists, so no email is sent, but the response is the neutral 202.
    assert response.status_code == 202
    assert email_sender.sent == []


async def test_register_rejects_weak_password(client: AsyncClient) -> None:
    response = await client.post(
        "/api/auth/register", json={"email": EMAIL, "password": "short"}
    )
    assert response.status_code == 400
    assert "at least 12 characters" in response.json()["detail"].lower()


async def test_register_rejects_pwned_password(
    client: AsyncClient, pwned_checker: StubPwnedChecker
) -> None:
    pwned_checker.times = 42
    response = await client.post(
        "/api/auth/register", json={"email": EMAIL, "password": PASSWORD}
    )
    assert response.status_code == 400
    assert "data breach" in response.json()["detail"].lower()


async def test_register_rejects_password_containing_email(client: AsyncClient) -> None:
    response = await client.post(
        "/api/auth/register", json={"email": EMAIL, "password": f"{EMAIL}-1"}
    )
    assert response.status_code == 400
    assert "must not contain your email" in response.json()["detail"].lower()


async def test_register_rejects_disposable_email(client: AsyncClient) -> None:
    response = await client.post(
        "/api/auth/register",
        json={"email": "throwaway@mailinator.com", "password": PASSWORD},
    )
    assert response.status_code == 400
    assert "disposable email" in response.json()["detail"].lower()


async def test_register_disposable_email_creates_no_account(
    client: AsyncClient,
    email_sender: CapturingEmailSender,
) -> None:
    await client.post(
        "/api/auth/register",
        json={"email": "throwaway@mailinator.com", "password": PASSWORD},
    )
    # Rejected before creation: no verification email, and login finds no user.
    assert email_sender.sent == []
    login = await _login(client, email="throwaway@mailinator.com")
    assert login.status_code == 400


async def test_verify_with_invalid_token_is_rejected(client: AsyncClient) -> None:
    response = await client.post("/api/auth/verify", json={"token": "not-a-token"})
    assert response.status_code == 400
    assert response.json()["detail"] == "VERIFY_USER_BAD_TOKEN"


async def test_request_verify_token_sends_when_unverified(
    client: AsyncClient,
    email_sender: CapturingEmailSender,
) -> None:
    await _register(client)
    email_sender.sent.clear()
    response = await client.post(
        "/api/auth/request-verify-token", json={"email": EMAIL}
    )
    assert response.status_code == 202
    assert any(e.kind == VERIFY for e in email_sender.sent)


async def test_users_me_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/users/me")
    assert response.status_code == 401


async def test_logout_clears_cookie(
    client: AsyncClient,
    email_sender: CapturingEmailSender,
) -> None:
    await _register(client)
    await _verify(client, email_sender)
    await _login(client)
    logout = await client.post("/api/auth/logout")
    assert logout.status_code == 204
    # After logout the protected endpoint is unauthorized again.
    me = await client.get("/api/users/me")
    assert me.status_code == 401
