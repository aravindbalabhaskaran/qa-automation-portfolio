import pytest
from jsonschema import validate

from tests.support import schemas
from tests.support.data import ENGINE_OIL, OUT_OF_STOCK

pytestmark = pytest.mark.api


@pytest.mark.smoke
def test_health_check(api):
    response = api.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.smoke
def test_list_products_matches_contract(api):
    response = api.get("/api/products")

    assert response.status_code == 200
    body = response.json()
    validate(body, schemas.PRODUCT_LIST)
    assert body["total"] == 6
    assert len(body["items"]) == 6
    ids = [p["id"] for p in body["items"]]
    assert len(set(ids)) == len(ids), "product ids must be unique"


@pytest.mark.regression
def test_default_sort_is_by_name(api):
    names = [p["name"] for p in api.get("/api/products").json()["items"]]

    assert names == sorted(names, key=str.lower)


@pytest.mark.regression
@pytest.mark.parametrize("sort, reverse", [("price_asc", False), ("price_desc", True)])
def test_sort_by_price(api, sort, reverse):
    prices = [p["price"] for p in api.get("/api/products", params={"sort": sort}).json()["items"]]

    assert prices == sorted(prices, reverse=reverse)


@pytest.mark.regression
@pytest.mark.parametrize(
    "query, expected",
    [("oil", ["Engine Oil 5W-30"]), ("OIL", ["Engine Oil 5W-30"]), ("gauge", ["Tyre Pressure Gauge"]), ("zzz", [])],
)
def test_search_by_name(api, query, expected):
    body = api.get("/api/products", params={"q": query}).json()

    assert [p["name"] for p in body["items"]] == expected
    assert body["total"] == len(expected)


@pytest.mark.regression
def test_filter_by_category(api):
    body = api.get("/api/products", params={"category": "tools"}).json()

    assert body["total"] == 3
    assert {p["category"] for p in body["items"]} == {"tools"}


@pytest.mark.regression
def test_pagination_returns_pages_without_overlap(api):
    first = api.get("/api/products", params={"limit": 4, "offset": 0}).json()
    second = api.get("/api/products", params={"limit": 4, "offset": 4}).json()

    assert len(first["items"]) == 4
    assert len(second["items"]) == 2
    assert first["total"] == second["total"] == 6
    assert not {p["id"] for p in first["items"]} & {p["id"] for p in second["items"]}


@pytest.mark.regression
def test_offset_past_the_end_returns_empty_page(api):
    body = api.get("/api/products", params={"offset": 100}).json()

    assert body["items"] == []
    assert body["total"] == 6


@pytest.mark.regression
@pytest.mark.parametrize(
    "params",
    [{"sort": "colour"}, {"limit": 0}, {"limit": 51}, {"limit": "abc"}, {"offset": -1}, {"offset": "x"}],
    ids=["bad-sort", "limit-zero", "limit-too-big", "limit-text", "negative-offset", "offset-text"],
)
def test_invalid_query_parameters_return_400(api, params):
    response = api.get("/api/products", params=params)

    assert response.status_code == 400
    validate(response.json(), schemas.ERROR)


@pytest.mark.smoke
def test_get_single_product(api):
    response = api.get(f"/api/products/{ENGINE_OIL}")

    assert response.status_code == 200
    body = response.json()
    validate(body, schemas.PRODUCT)
    assert body["name"] == "Engine Oil 5W-30"
    assert body["price"] == 32.5


@pytest.mark.regression
def test_out_of_stock_product_reports_zero_stock(api):
    assert api.get(f"/api/products/{OUT_OF_STOCK}").json()["stock"] == 0


@pytest.mark.regression
@pytest.mark.parametrize("product_id", ["999", "0", "-1"])
def test_unknown_product_returns_404_json(api, product_id):
    response = api.get(f"/api/products/{product_id}")

    assert response.status_code == 404
    validate(response.json(), schemas.ERROR)


@pytest.mark.regression
def test_non_numeric_product_id_returns_404_json(api):
    response = api.get("/api/products/abc")

    assert response.status_code == 404
    assert response.headers["Content-Type"].startswith("application/json")


@pytest.mark.regression
def test_wrong_method_returns_405_json(api):
    response = api.post("/api/products", json={})

    assert response.status_code == 405
    validate(response.json(), schemas.ERROR)
