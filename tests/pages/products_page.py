from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from .base_page import BasePage


class ProductsPage(BasePage):
    path = "/products"

    def __init__(self, page: Page):
        super().__init__(page)
        self.heading = page.get_by_role("heading", name="Products")
        self.cards = page.get_by_test_id("product-card")
        self.search_box = page.get_by_role("searchbox", name="Search products")
        self.sort_select = page.get_by_label("Sort products")
        self.empty_state = page.get_by_test_id("empty-state")

    def card(self, name: str) -> Locator:
        return self.cards.filter(has=self.page.get_by_test_id("product-name").get_by_text(name, exact=True))

    def add_to_cart(self, name: str):
        self.card(name).get_by_role("button", name="Add to cart").click()
        return self

    def search(self, text: str):
        """Type into the search box and wait for the API call it triggers."""
        with self.page.expect_response(lambda r: "/api/products" in r.url and r.request.method == "GET") as info:
            self.search_box.fill(text)
        return info.value

    def sort_by(self, value: str):
        with self.page.expect_response(lambda r: "/api/products" in r.url and f"sort={value}" in r.url):
            self.sort_select.select_option(value)

    def names(self) -> list[str]:
        return self.cards.get_by_test_id("product-name").all_inner_texts()

    def prices(self) -> list[float]:
        return [float(t.replace("€", "")) for t in self.cards.get_by_test_id("product-price").all_inner_texts()]

    def expect_loaded(self, count: int | None = None):
        expect(self.heading).to_be_visible()
        if count is not None:
            expect(self.cards).to_have_count(count)
