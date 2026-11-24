import pytest
from jsonschema import validate

from tests.support import schemas
from tests.support.data import LOCKED_USER, VALID_USER

pytestmark = pytest.mark.api


@pytest.mark.smoke
def test_login_returns_a_token(api):
    response = api.login(**VALID_USER)

    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("application/json")
    body = response.json()
    validate(body, schemas.LOGIN)
    assert body["username"] == "tester"


@pytest.mark.regression
def test_tokens_are_unique_per_login(api):
    first = api.login(**VALID_USER).json()["token"]
    second = api.login(**VALID_USER).json()["token"]

    assert first != second


@pytest.mark.regression
@pytest.mark.parametrize(
    "payload, status",
    [
        ({"username": "tester", "password": "wrong"}, 401),
        ({"username": "nobody", "password": "Test@1234"}, 401),
        ({"username": "tester"}, 400),
        ({"password": "Test@1234"}, 400),
        ({}, 400),
    ],
    ids=["wrong-password", "unknown-user", "missing-password", "missing-username", "empty-body"],
)
def test_login_rejects_bad_requests(api, payload, status):
    response = api.post("/api/auth/login", json=payload)

    assert response.status_code == status
    validate(response.json(), schemas.ERROR)


@pytest.mark.regression
def test_login_with_non_json_body_is_a_client_error(api):
    response = api.post("/api/auth/login", data="username=tester&password=Test@1234")

    assert response.status_code == 400


@pytest.mark.regression
def test_locked_account_gets_403(api):
    response = api.login(**LOCKED_USER)

    assert response.status_code == 403
    assert response.json()["error"] == "This account is locked"


@pytest.mark.regression
@pytest.mark.parametrize(
    "method, path",
    [("GET", "/api/orders"), ("POST", "/api/orders"), ("GET", "/api/orders/1"), ("DELETE", "/api/orders/1")],
)
def test_protected_endpoints_require_a_token(api, method, path):
    response = api.request(method, path)

    assert response.status_code == 401
    validate(response.json(), schemas.ERROR)


@pytest.mark.regression
def test_invalid_token_is_rejected(api):
    response = api.with_token("not-a-real-token").get("/api/orders")

    assert response.status_code == 401
