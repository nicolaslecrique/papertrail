"""End-to-end browser test for the login / logout flow (real htmx + cookies)."""

from playwright.sync_api import Page, expect


def test_login_and_logout(
    live_server: str,
    verified_credentials: tuple[str, str],
    page: Page,
) -> None:
    email, password = verified_credentials

    # The protected page bounces an anonymous visitor to sign in.
    page.goto(f"{live_server}/dashboard")
    expect(page).to_have_url(f"{live_server}/login")

    # Sign in with the seeded, verified account.
    page.get_by_label("Email").fill(email)
    page.get_by_label("Password").fill(password)
    page.get_by_role("button", name="Sign in").click()

    expect(page).to_have_url(f"{live_server}/dashboard")
    expect(page.get_by_text(email)).to_be_visible()

    # Logging out returns to the sign-in page.
    page.get_by_role("button", name="Log out").click()
    expect(page).to_have_url(f"{live_server}/login")
