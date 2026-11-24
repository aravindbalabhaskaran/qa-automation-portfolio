from __future__ import annotations

import re

from playwright.sync_api import Page, expect


class BasePage:
    path = "/"

    def __init__(self, page: Page):
        self.page = page
        self.cart_badge = page.get_by_test_id("cart-badge")
        self.cart_link = page.get_by_test_id("cart-link")
        self.logout_link = page.get_by_test_id("logout")
        self.current_user = page.get_by_test_id("current-user")

    def open(self):
        self.page.goto(self.path)
        return self

    def cart_count(self) -> int:
        return int(self.cart_badge.inner_text())

    def log_out(self):
        self.logout_link.click()

    def expect_url_path(self, path: str):
        expect(self.page).to_have_url(re.compile(rf"{re.escape(path)}$"))
