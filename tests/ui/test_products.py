import pytest
from playwright.sync_api import expect

from tests.pages.products_page import ProductsPage

pytestmark = pytest.mark.ui


@pytest.fixture
def products(logged_in_page) -> ProductsPage:
    page = ProductsPage(logged_in_page)
    page.expect_loaded(count=6)
    return page


@pytest.mark.smoke
def test_add_to_cart_updates_the_badge(products):
    expect(products.cart_badge).to_have_text("0")

    products.add_to_cart("Brake Pad Set")
    expect(products.cart_badge).to_have_text("1")

    products.add_to_cart("Engine Oil 5W-30")
    expect(products.cart_badge).to_have_text("2")


@pytest.mark.regression
def test_search_filters_the_list_and_calls_the_api(products):
    response = products.search("oil")

    assert response.status == 200
    assert "q=oil" in response.url
    expect(products.cards).to_have_count(1)
    expect(products.cards.first).to_contain_text("Engine Oil 5W-30")


@pytest.mark.regression
def test_search_is_case_insensitive(products):
    products.search("OBD")

    expect(products.cards).to_have_count(1)
    expect(products.card("OBD-II Scanner")).to_be_visible()


@pytest.mark.regression
def test_search_without_matches_shows_empty_state(products):
    products.search("flux capacitor")

    expect(products.cards).to_have_count(0)
    expect(products.empty_state).to_be_visible()
    expect(products.empty_state).to_have_text("No products found")


@pytest.mark.regression
def test_clearing_search_restores_all_products(products):
    products.search("oil")
    expect(products.cards).to_have_count(1)

    products.search("")

    expect(products.cards).to_have_count(6)
    expect(products.empty_state).to_be_hidden()


@pytest.mark.regression
def test_sort_by_price_low_to_high(products):
    products.sort_by("price_asc")

    expect(products.cards.first).to_contain_text("Tyre Pressure Gauge")  # cheapest, 12.90
    prices = products.prices()
    assert prices == sorted(prices)


@pytest.mark.regression
def test_sort_by_price_high_to_low(products):
    products.sort_by("price_desc")

    expect(products.cards.first).to_contain_text("OBD-II Scanner")  # most expensive, 79.00
    prices = products.prices()
    assert prices == sorted(prices, reverse=True)


@pytest.mark.regression
def test_out_of_stock_product_cannot_be_added(products):
    button = products.card("Digital Multimeter").get_by_role("button")

    expect(button).to_be_disabled()
    expect(button).to_have_text("Out of stock")
    expect(products.cart_badge).to_have_text("0")
