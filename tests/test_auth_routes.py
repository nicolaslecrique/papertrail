"""Integration tests for the auth flows, driven through the HTTP layer.

These exercise the full stack (routes -> UserManager -> Postgres) with a fake
email sender that captures the verification / reset tokens the flows emit.
"""

import pytest
from conftest import CapturingEmailSender
from httpx import AsyncClient

VERIFY = "verify"
RESET = "reset"

EMAIL = "alice@example.com"
PASSWORD = "sup3r-secret-pw"
NEW_PASSWORD = "an0ther-secret-pw"


async def _register(
    client: AsyncClient, email: str = EMAIL, password: str = PASSWORD
) -> None:
    response = await client.post(
        "/register",
        data={"email": email, "password": password, "confirm_password": password},
    )
    assert response.status_code == 200


async def _verify(client: AsyncClient, sender: CapturingEmailSender) -> None:
    token = sender.last_token(VERIFY)
    response = await client.get("/verify", params={"token": token})
    assert response.status_code == 200
    assert "confirmed" in response.text.lower()


async def test_register_sends_verification_email(
    client: AsyncClient,
    email_sender: CapturingEmailSender,
) -> None:
    await _register(client)
    assert any(e.kind == VERIFY and e.email == EMAIL for e in email_sender.sent)


async def test_login_blocked_until_verified(
    client: AsyncClient,
    email_sender: CapturingEmailSender,
) -> None:
    await _register(client)
    response = await client.post("/login", data={"email": EMAIL, "password": PASSWORD})
    assert response.status_code == 200
    assert "confirm your email" in response.text.lower()
    assert "HX-Redirect" not in response.headers
    # No verification email was sent by the login attempt itself.
    assert all(e.kind == VERIFY for e in email_sender.sent)


async def test_verify_then_login_sets_cookie(
    client: AsyncClient,
    email_sender: CapturingEmailSender,
) -> None:
    await _register(client)
    await _verify(client, email_sender)
    response = await client.post("/login", data={"email": EMAIL, "password": PASSWORD})
    assert response.status_code == 204
    assert response.headers["HX-Redirect"] == "/dashboard"
    assert "papertrailauth" in response.headers.get("set-cookie", "")
    # The authenticated session now reaches the protected page.
    dashboard = await client.get("/dashboard")
    assert dashboard.status_code == 200
    assert EMAIL in dashboard.text


async def test_login_wrong_password_shows_error(
    client: AsyncClient,
    email_sender: CapturingEmailSender,
) -> None:
    await _register(client)
    await _verify(client, email_sender)
    response = await client.post(
        "/login", data={"email": EMAIL, "password": "wrong-password"}
    )
    assert response.status_code == 200
    assert "invalid email or password" in response.text.lower()
    assert "HX-Redirect" not in response.headers


async def test_forgot_then_reset_password(
    client: AsyncClient,
    email_sender: CapturingEmailSender,
) -> None:
    await _register(client)
    await _verify(client, email_sender)
    forgot = await client.post("/forgot-password", data={"email": EMAIL})
    assert forgot.status_code == 200
    token = email_sender.last_token(RESET)
    reset = await client.post(
        "/reset-password",
        data={
            "token": token,
            "password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD,
        },
    )
    assert reset.status_code == 200
    assert reset.headers["HX-Redirect"] == "/login"
    # The new password now works and the old one does not.
    ok = await client.post("/login", data={"email": EMAIL, "password": NEW_PASSWORD})
    assert ok.status_code == 204
    bad = await client.post("/login", data={"email": EMAIL, "password": PASSWORD})
    assert bad.status_code == 200
    assert "invalid email or password" in bad.text.lower()


async def test_reset_password_with_invalid_token(client: AsyncClient) -> None:
    response = await client.post(
        "/reset-password",
        data={
            "token": "not-a-real-token",
            "password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD,
        },
    )
    assert response.status_code == 200
    assert "invalid or has expired" in response.text.lower()


async def test_forgot_password_does_not_enumerate(
    client: AsyncClient,
    email_sender: CapturingEmailSender,
) -> None:
    known = await client.post("/forgot-password", data={"email": "nobody@example.com"})
    assert known.status_code == 200
    # No account exists, so no email is sent, but the response is the neutral one.
    assert email_sender.sent == []
    assert "if an account exists" in known.text.lower()


async def test_register_rejects_weak_password(client: AsyncClient) -> None:
    response = await client.post(
        "/register",
        data={"email": EMAIL, "password": "short", "confirm_password": "short"},
    )
    assert response.status_code == 200
    assert "at least 8 characters" in response.text.lower()


async def test_register_rejects_password_containing_email(client: AsyncClient) -> None:
    response = await client.post(
        "/register",
        data={
            "email": EMAIL,
            "password": f"{EMAIL}-1",
            "confirm_password": f"{EMAIL}-1",
        },
    )
    assert response.status_code == 200
    assert "must not contain your email" in response.text.lower()


async def test_register_rejects_mismatched_passwords(client: AsyncClient) -> None:
    response = await client.post(
        "/register",
        data={"email": EMAIL, "password": PASSWORD, "confirm_password": "different"},
    )
    assert response.status_code == 200
    assert "do not match" in response.text.lower()


@pytest.mark.parametrize(
    ("path", "marker"),
    [
        ("/login", 'hx-post="/login"'),
        ("/register", 'hx-post="/register"'),
        ("/forgot-password", 'hx-post="/forgot-password"'),
        ("/reset-password?token=abc", 'value="abc"'),
    ],
)
async def test_auth_pages_render(client: AsyncClient, path: str, marker: str) -> None:
    response = await client.get(path)
    assert response.status_code == 200
    assert marker in response.text


async def test_verify_with_invalid_token_shows_failure(client: AsyncClient) -> None:
    response = await client.get("/verify", params={"token": "not-a-token"})
    assert response.status_code == 200
    assert "confirmation failed" in response.text.lower()


async def test_resend_verification_sends_when_unverified(
    client: AsyncClient,
    email_sender: CapturingEmailSender,
) -> None:
    await _register(client)
    email_sender.sent.clear()
    response = await client.post("/resend-verification", data={"email": EMAIL})
    assert response.status_code == 200
    assert any(e.kind == VERIFY for e in email_sender.sent)


async def test_dashboard_redirects_when_anonymous(client: AsyncClient) -> None:
    response = await client.get("/dashboard")
    assert response.status_code == 302
    assert response.headers["location"] == "/login"


async def test_logout_clears_cookie(
    client: AsyncClient,
    email_sender: CapturingEmailSender,
) -> None:
    await _register(client)
    await _verify(client, email_sender)
    await client.post("/login", data={"email": EMAIL, "password": PASSWORD})
    logout = await client.post("/logout")
    assert logout.headers["HX-Redirect"] == "/login"
    # After logout the protected page redirects again.
    dashboard = await client.get("/dashboard")
    assert dashboard.status_code == 302
