from __future__ import annotations

from playwright.sync_api import Page, expect

from .base_page import BasePage


class LoginPage(BasePage):
    path = "/login"

    def __init__(self, page: Page):
        super().__init__(page)
        self.username = page.get_by_label("Username")
        self.password = page.get_by_label("Password")
        self.submit = page.get_by_role("button", name="Log in")
        self.error = page.get_by_test_id("login-error")

    def log_in(self, username: str, password: str):
        self.username.fill(username)
        self.password.fill(password)
        self.submit.click()
        return self

    def expect_error(self, message: str):
        expect(self.error).to_have_text(message)
