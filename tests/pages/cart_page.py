from __future__ import annotations

from playwright.sync_api import Page

from .base_page import BasePage


class CartPage(BasePage):
    path = "/cart"

    def __init__(self, page: Page):
        super().__init__(page)
        self.items = page.get_by_test_id("cart-item")
        self.total = page.get_by_test_id("cart-total")
        self.empty_message = page.get_by_test_id("cart-empty")
        self.checkout_button = page.get_by_test_id("checkout-button")

    def item(self, name: str):
        return self.items.filter(has_text=name)

    def remove(self, name: str):
        self.item(name).get_by_role("button", name="Remove").click()
        return self

    def go_to_checkout(self):
        self.checkout_button.click()
