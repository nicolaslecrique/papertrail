"""End-to-end test driving the real htmx interaction in a headless browser."""

from playwright.sync_api import Page, expect


def test_greet_swaps_in_greeting(live_server: str, page: Page) -> None:
    page.goto(live_server)
    expect(page.get_by_role("heading", name="Hello World")).to_be_visible()
    page.get_by_label("Your name").fill("Ada")
    page.get_by_role("button", name="Greet me").click()
    expect(page.get_by_text("Hello, Ada!")).to_be_visible()
