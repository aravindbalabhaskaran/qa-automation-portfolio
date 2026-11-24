"""Thin wrapper around requests so tests read like the API they exercise."""
from __future__ import annotations

import requests

DEFAULT_TIMEOUT = 5  # seconds; never let a hung request stall the suite


class ApiClient:
    def __init__(self, base_url: str, token: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.token = token

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        headers = kwargs.pop("headers", {})
        if self.token:
            headers.setdefault("Authorization", f"Bearer {self.token}")
        kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
        return self.session.request(method, f"{self.base_url}{path}", headers=headers, **kwargs)

    def get(self, path: str, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs):
        return self.request("POST", path, **kwargs)

    def delete(self, path: str, **kwargs):
        return self.request("DELETE", path, **kwargs)

    def login(self, username: str, password: str) -> requests.Response:
        return self.post("/api/auth/login", json={"username": username, "password": password})

    def with_token(self, token: str) -> "ApiClient":
        return ApiClient(self.base_url, token)
