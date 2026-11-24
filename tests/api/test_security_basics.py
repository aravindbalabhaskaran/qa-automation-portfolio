"""A few cheap negative checks that catch common mistakes."""
import pytest

from tests.support.data import ENGINE_OIL, SHIPPING

pytestmark = pytest.mark.api


@pytest.mark.regression
def test_error_responses_do_not_leak_stack_traces(api):
    response = api.get("/api/products", params={"limit": "abc"})

    text = response.text.lower()
    assert "traceback" not in text
    assert "werkzeug" not in text


@pytest.mark.regression
def test_sql_like_search_input_is_treated_as_plain_text(api):
    response = api.get("/api/products", params={"q": "' OR 1=1 --"})

    assert response.status_code == 200
    assert response.json()["items"] == []


@pytest.mark.regression
def test_markup_in_shipping_name_is_stored_as_plain_text(auth_api):
    payload = {"items": [{"product_id": ENGINE_OIL, "quantity": 1}],
               "shipping": {**SHIPPING, "name": "<script>alert(1)</script>"}}

    response = auth_api.post("/api/orders", json=payload)

    # The API stores text as-is; escaping on output is the renderer's job.
    assert response.status_code == 201
    assert response.json()["shipping"]["name"] == "<script>alert(1)</script>"
