"""Keeps the Postman collection honest.

Newman is the real runner for the collection (see README), but it needs Node.
This test replays the same requests with ``requests`` and checks every
``pm.response.to.have.status(N)`` assertion and the variables the collection
passes between requests (token, orderId). If the API changes and someone forgets
to update the collection, this fails in the normal pytest run.
"""
import json
import re
from pathlib import Path

import pytest
import requests

pytestmark = [pytest.mark.api, pytest.mark.regression]

COLLECTION = Path(__file__).resolve().parents[2] / "postman" / "parts-shop.postman_collection.json"
STATUS_RE = re.compile(r"pm\.response\.to\.have\.status\((\d+)\)")
SET_VAR_RE = re.compile(r'pm\.collectionVariables\.set\("(\w+)",\s*json\.(\w+)\)')


def _requests_in_order(collection):
    for folder in collection["item"]:
        yield from folder["item"]


def _substitute(text: str, variables: dict) -> str:
    return re.sub(r"\{\{(\w+)\}\}", lambda m: str(variables[m.group(1)]), text)


def test_postman_collection_replays_green(base_url):
    collection = json.loads(COLLECTION.read_text())
    variables = {"baseUrl": base_url, **{v["key"]: v["value"] for v in collection["variable"]}}

    count = 0
    for item in _requests_in_order(collection):
        spec = item["request"]
        script = "\n".join(item["event"][0]["script"]["exec"])
        expected = [int(s) for s in STATUS_RE.findall(script)]
        assert expected, f"{item['name']!r} has no status assertion"

        headers = {h["key"]: h["value"] for h in spec["header"]}
        if spec.get("auth", {}).get("type") != "noauth" and variables.get("token"):
            headers["Authorization"] = f"Bearer {variables['token']}"
        body = _substitute(spec["body"]["raw"], variables) if "body" in spec else None

        response = requests.request(
            spec["method"], _substitute(spec["url"]["raw"], variables),
            headers=headers, data=body, timeout=5,
        )
        assert response.status_code in expected, f"{item['name']!r}: got {response.status_code}, expected {expected}"

        for var, field in SET_VAR_RE.findall(script):
            variables[var] = response.json()[field]
        count += 1

    assert count >= 15
