import pytest
from jsonschema import validate

from tests.support import schemas
from tests.support.data import BRAKE_PADS, ENGINE_OIL, OBD_SCANNER, OUT_OF_STOCK, SHIPPING, TYRE_GAUGE

pytestmark = pytest.mark.api


def order_body(*lines, shipping=SHIPPING):
    return {"items": [{"product_id": pid, "quantity": qty} for pid, qty in lines], "shipping": shipping}


def stock_of(api, product_id):
    return api.get(f"/api/products/{product_id}").json()["stock"]


@pytest.mark.smoke
def test_create_order_returns_201_and_correct_total(auth_api):
    response = auth_api.post("/api/orders", json=order_body((BRAKE_PADS, 2), (TYRE_GAUGE, 1)))

    assert response.status_code == 201
    order = response.json()
    validate(order, schemas.ORDER)
    assert order["status"] == "CREATED"
    assert order["total"] == 112.70  # 2 x 49.90 + 12.90
    assert order["user"] == "tester"


@pytest.mark.regression
def test_create_order_reduces_stock(auth_api):
    before = stock_of(auth_api, OBD_SCANNER)

    auth_api.post("/api/orders", json=order_body((OBD_SCANNER, 3)))

    assert stock_of(auth_api, OBD_SCANNER) == before - 3


@pytest.mark.regression
def test_same_product_on_two_lines_is_combined(auth_api):
    response = auth_api.post("/api/orders", json=order_body((ENGINE_OIL, 1), (ENGINE_OIL, 2)))

    assert response.status_code == 201
    assert response.json()["items"][0]["quantity"] == 3
    assert response.json()["total"] == 97.50


@pytest.mark.regression
def test_order_ids_increase(auth_api):
    first = auth_api.post("/api/orders", json=order_body((ENGINE_OIL, 1))).json()["id"]
    second = auth_api.post("/api/orders", json=order_body((ENGINE_OIL, 1))).json()["id"]

    assert second == first + 1


@pytest.mark.regression
def test_get_order_by_id(auth_api):
    created = auth_api.post("/api/orders", json=order_body((BRAKE_PADS, 1))).json()

    response = auth_api.get(f"/api/orders/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


@pytest.mark.regression
def test_list_orders_contains_only_my_orders(auth_api):
    assert auth_api.get("/api/orders").json()["total"] == 0
    auth_api.post("/api/orders", json=order_body((BRAKE_PADS, 1)))
    auth_api.post("/api/orders", json=order_body((ENGINE_OIL, 1)))

    body = auth_api.get("/api/orders").json()

    validate(body, schemas.ORDER_LIST)
    assert body["total"] == 2


@pytest.mark.regression
def test_unknown_order_returns_404(auth_api):
    response = auth_api.get("/api/orders/9999")

    assert response.status_code == 404
    validate(response.json(), schemas.ERROR)


@pytest.mark.regression
def test_cancel_order_restores_stock(auth_api):
    before = stock_of(auth_api, BRAKE_PADS)
    order_id = auth_api.post("/api/orders", json=order_body((BRAKE_PADS, 4))).json()["id"]
    assert stock_of(auth_api, BRAKE_PADS) == before - 4

    response = auth_api.delete(f"/api/orders/{order_id}")

    assert response.status_code == 204
    assert response.content == b""
    assert stock_of(auth_api, BRAKE_PADS) == before
    assert auth_api.get(f"/api/orders/{order_id}").status_code == 404


@pytest.mark.regression
def test_cancelling_twice_returns_404_and_does_not_restock_again(auth_api):
    before = stock_of(auth_api, BRAKE_PADS)
    order_id = auth_api.post("/api/orders", json=order_body((BRAKE_PADS, 2))).json()["id"]
    auth_api.delete(f"/api/orders/{order_id}")

    second = auth_api.delete(f"/api/orders/{order_id}")

    assert second.status_code == 404
    assert stock_of(auth_api, BRAKE_PADS) == before


@pytest.mark.regression
def test_out_of_stock_product_returns_409(auth_api):
    response = auth_api.post("/api/orders", json=order_body((OUT_OF_STOCK, 1)))

    assert response.status_code == 409
    assert "out of stock" in response.json()["error"]


@pytest.mark.regression
def test_ordering_more_than_stock_returns_409_and_changes_nothing(auth_api):
    # OBD scanner: stock 10, max 10 per line, so buy 6 then ask for 6 more
    assert auth_api.post("/api/orders", json=order_body((OBD_SCANNER, 6))).status_code == 201

    response = auth_api.post("/api/orders", json=order_body((OBD_SCANNER, 6)))

    assert response.status_code == 409
    assert response.json()["error"] == "Only 4 left of OBD-II Scanner"
    assert stock_of(auth_api, OBD_SCANNER) == 4


@pytest.mark.regression
def test_failed_line_does_not_reserve_stock_for_other_lines(auth_api):
    before = stock_of(auth_api, BRAKE_PADS)

    response = auth_api.post("/api/orders", json=order_body((BRAKE_PADS, 1), (OUT_OF_STOCK, 1)))

    assert response.status_code == 409
    assert stock_of(auth_api, BRAKE_PADS) == before, "stock must not change when the order fails"


@pytest.mark.regression
def test_unknown_product_returns_404(auth_api):
    response = auth_api.post("/api/orders", json=order_body((999, 1)))

    assert response.status_code == 404


@pytest.mark.regression
@pytest.mark.parametrize("quantity", [0, -1, 11, 1.5, "2", None, True])
def test_invalid_quantity_returns_400(auth_api, quantity):
    body = {"items": [{"product_id": ENGINE_OIL, "quantity": quantity}], "shipping": SHIPPING}

    response = auth_api.post("/api/orders", json=body)

    assert response.status_code == 400
    validate(response.json(), schemas.ERROR)


@pytest.mark.regression
@pytest.mark.parametrize(
    "body",
    [
        {},
        {"items": [], "shipping": SHIPPING},
        {"items": "oil", "shipping": SHIPPING},
        {"items": [{"quantity": 1}], "shipping": SHIPPING},
        {"items": [{"product_id": "1", "quantity": 1}], "shipping": SHIPPING},
        {"items": [{"product_id": ENGINE_OIL, "quantity": 1}]},
        {"items": [{"product_id": ENGINE_OIL, "quantity": 1}], "shipping": {"name": "", "postal_code": "12459"}},
        {"items": [{"product_id": ENGINE_OIL, "quantity": 1}], "shipping": {"name": "A", "postal_code": "1245"}},
        {"items": [{"product_id": ENGINE_OIL, "quantity": 1}], "shipping": {"name": "A", "postal_code": "ABCDE"}},
    ],
    ids=["empty", "no-items", "items-not-list", "no-product-id", "product-id-string", "no-shipping",
         "blank-name", "short-postal", "alpha-postal"],
)
def test_malformed_order_returns_400(auth_api, body):
    response = auth_api.post("/api/orders", json=body)

    assert response.status_code == 400
    validate(response.json(), schemas.ERROR)
