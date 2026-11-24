from __future__ import annotations

from playwright.sync_api import Page, expect

from .base_page import BasePage


class CheckoutPage(BasePage):
    path = "/checkout"

    def __init__(self, page: Page):
        super().__init__(page)
        self.name = page.get_by_label("Full name")
        self.postal_code = page.get_by_label("Postal code")
        self.place_order = page.get_by_role("button", name="Place order")
        self.error = page.get_by_test_id("checkout-error")

    def submit(self, name: str, postal_code: str):
        self.name.fill(name)
        self.postal_code.fill(postal_code)
        self.place_order.click()
        return self

    def expect_error(self, message: str):
        expect(self.error).to_have_text(message)


class ConfirmationPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.title = page.get_by_test_id("confirmation-title")
        self.order_id = page.get_by_test_id("order-id")
        self.total = page.get_by_test_id("order-total")
