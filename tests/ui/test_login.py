import pytest
from playwright.sync_api import expect

from tests.pages.login_page import LoginPage
from tests.pages.products_page import ProductsPage
from tests.support.data import LOCKED_USER, VALID_USER

pytestmark = pytest.mark.ui


@pytest.mark.smoke
def test_valid_user_lands_on_products_page(page):
    LoginPage(page).open().log_in(**VALID_USER)

    products = ProductsPage(page)
    products.expect_url_path("/products")
    products.expect_loaded(count=6)
    expect(products.current_user).to_have_text("tester")


@pytest.mark.regression
@pytest.mark.parametrize(
    "username, password, message",
    [
        ("tester", "wrong-password", "Invalid username or password"),
        ("nobody", "Test@1234", "Invalid username or password"),
        ("", "Test@1234", "Username and password are required"),
        ("tester", "", "Username and password are required"),
        ("", "", "Username and password are required"),
    ],
    ids=["wrong-password", "unknown-user", "no-username", "no-password", "no-credentials"],
)
def test_invalid_credentials_show_an_error(page, username, password, message):
    login = LoginPage(page).open().log_in(username, password)

    login.expect_error(message)
    login.expect_url_path("/login")


@pytest.mark.regression
def test_locked_user_cannot_log_in(page):
    login = LoginPage(page).open().log_in(**LOCKED_USER)

    login.expect_error("This account is locked")


@pytest.mark.regression
@pytest.mark.parametrize("path", ["/products", "/cart", "/checkout"])
def test_protected_pages_redirect_anonymous_users_to_login(page, path):
    page.goto(path)

    LoginPage(page).expect_url_path("/login")


@pytest.mark.regression
def test_logout_ends_the_session(logged_in_page):
    products = ProductsPage(logged_in_page)
    products.log_out()

    products.expect_url_path("/login")
    logged_in_page.goto("/products")
    products.expect_url_path("/login")
