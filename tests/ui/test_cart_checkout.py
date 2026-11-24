import pytest
from playwright.sync_api import expect

from tests.pages.cart_page import CartPage
from tests.pages.checkout_page import CheckoutPage, ConfirmationPage
from tests.pages.products_page import ProductsPage
from tests.support.data import SHIPPING

pytestmark = pytest.mark.ui


@pytest.fixture
def products(logged_in_page) -> ProductsPage:
    page = ProductsPage(logged_in_page)
    page.expect_loaded(count=6)
    return page


@pytest.mark.smoke
def test_customer_can_buy_two_items(products, page):
    products.add_to_cart("Brake Pad Set")
    products.add_to_cart("Tyre Pressure Gauge")
    expect(products.cart_badge).to_have_text("2")

    products.cart_link.click()
    cart = CartPage(page)
    expect(cart.items).to_have_count(2)
    expect(cart.total).to_have_text("€62.80")  # 49.90 + 12.90

    cart.go_to_checkout()
    CheckoutPage(page).submit(**SHIPPING)

    confirmation = ConfirmationPage(page)
    expect(confirmation.title).to_be_visible()
    expect(confirmation.total).to_have_text("€62.80")
    expect(confirmation.order_id).to_have_text("1")


@pytest.mark.regression
def test_same_product_twice_increases_quantity(products, page):
    products.add_to_cart("OBD-II Scanner")
    products.add_to_cart("OBD-II Scanner")

    products.cart_link.click()
    cart = CartPage(page)
    expect(cart.items).to_have_count(1)
    expect(cart.item("OBD-II Scanner").get_by_test_id("cart-item-qty")).to_have_text("2")
    expect(cart.total).to_have_text("€158.00")


@pytest.mark.regression
def test_removing_an_item_updates_the_total(products, page):
    products.add_to_cart("Brake Pad Set")
    products.add_to_cart("Engine Oil 5W-30")
    products.cart_link.click()
    cart = CartPage(page)
    expect(cart.total).to_have_text("€82.40")

    cart.remove("Brake Pad Set")

    expect(cart.items).to_have_count(1)
    expect(cart.total).to_have_text("€32.50")


@pytest.mark.regression
def test_empty_cart_shows_message_and_no_checkout(logged_in_page):
    cart = CartPage(logged_in_page).open()

    expect(cart.empty_message).to_have_text("Your cart is empty")
    expect(cart.checkout_button).to_have_count(0)


@pytest.mark.regression
def test_removing_the_last_item_empties_the_cart(products, page):
    products.add_to_cart("Brake Pad Set")
    products.cart_link.click()
    cart = CartPage(page)

    cart.remove("Brake Pad Set")

    expect(cart.empty_message).to_be_visible()


@pytest.mark.regression
@pytest.mark.parametrize(
    "name, postal_code, message",
    [
        ("", "12459", "shipping.name is required"),
        ("   ", "12459", "shipping.name is required"),
        ("Aravind B", "", "shipping.postal_code must be 5 digits"),
        ("Aravind B", "1245", "shipping.postal_code must be 5 digits"),
        ("Aravind B", "124599", "shipping.postal_code must be 5 digits"),
        ("Aravind B", "12A59", "shipping.postal_code must be 5 digits"),
    ],
    ids=["no-name", "blank-name", "no-postal", "postal-too-short", "postal-too-long", "postal-letters"],
)
def test_checkout_validation(products, page, name, postal_code, message):
    products.add_to_cart("Engine Oil 5W-30")
    products.cart_link.click()
    CartPage(page).go_to_checkout()

    checkout = CheckoutPage(page).submit(name, postal_code)

    checkout.expect_error(message)
    expect(ConfirmationPage(page).title).to_have_count(0)
