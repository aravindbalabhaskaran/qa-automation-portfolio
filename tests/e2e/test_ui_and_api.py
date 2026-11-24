"""Flows that cross both layers: act in the browser, verify through the API."""
import pytest
from playwright.sync_api import expect

from tests.pages.cart_page import CartPage
from tests.pages.checkout_page import CheckoutPage, ConfirmationPage
from tests.pages.products_page import ProductsPage
from tests.support.data import ENGINE_OIL, SHIPPING

pytestmark = [pytest.mark.e2e, pytest.mark.ui, pytest.mark.api]


def _buy_oil_twice_in_ui(page) -> str:
    products = ProductsPage(page)
    products.expect_loaded(count=6)
    products.add_to_cart("Engine Oil 5W-30")
    products.add_to_cart("Engine Oil 5W-30")
    products.cart_link.click()
    CartPage(page).go_to_checkout()
    CheckoutPage(page).submit(**SHIPPING)
    confirmation = ConfirmationPage(page)
    expect(confirmation.title).to_be_visible()
    return confirmation.order_id.inner_text()


@pytest.mark.smoke
def test_order_placed_in_ui_is_stored_correctly(logged_in_page, auth_api):
    order_id = _buy_oil_twice_in_ui(logged_in_page)

    response = auth_api.get(f"/api/orders/{order_id}")

    assert response.status_code == 200
    order = response.json()
    assert order["total"] == 65.00  # 2 x 32.50
    assert order["shipping"] == SHIPPING
    assert order["items"] == [
        {"product_id": ENGINE_OIL, "name": "Engine Oil 5W-30", "quantity": 2, "unit_price": 32.5}
    ]


@pytest.mark.regression
def test_stock_is_reduced_after_checkout_in_ui(logged_in_page, api):
    before = api.get(f"/api/products/{ENGINE_OIL}").json()["stock"]

    _buy_oil_twice_in_ui(logged_in_page)

    after = api.get(f"/api/products/{ENGINE_OIL}").json()["stock"]
    assert after == before - 2


@pytest.mark.regression
def test_ui_shows_what_the_api_returns_for_search(logged_in_page, api):
    api_names = [p["name"] for p in api.get("/api/products", params={"q": "o", "sort": "name"}).json()["items"]]

    products = ProductsPage(logged_in_page)
    products.expect_loaded(count=6)
    products.search("o")

    expect(products.cards).to_have_count(len(api_names))
    assert products.names() == api_names
