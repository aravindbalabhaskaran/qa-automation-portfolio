"""Shared fixtures.

* ``base_url``  - starts the bundled demo app on a free port, or uses BASE_URL
                  if you point the suite at another environment.
* ``page``      - a fresh Playwright browser context per test, with tracing;
                  a screenshot and a trace are saved when the test fails.
* ``api``       - an unauthenticated API client; ``auth_api`` is logged in.
"""
from __future__ import annotations

import os
import re
import socket
import threading
import time
from pathlib import Path

import pytest
import requests
from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright
from werkzeug.serving import make_server

from demo_app.app import create_app
from tests.support.api_client import ApiClient
from tests.support.data import VALID_USER

ARTIFACTS = Path(os.getenv("ARTIFACTS_DIR", "artifacts"))


# ----------------------------------------------------------------- server
def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def base_url():
    external = os.getenv("BASE_URL")
    if external:
        yield external.rstrip("/")
        return
    server = make_server("127.0.0.1", _free_port(), create_app(enable_test_endpoints=True), threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            if requests.get(f"{url}/api/health", timeout=1).ok:
                break
        except requests.ConnectionError:
            time.sleep(0.1)
    else:
        raise RuntimeError("demo app did not start within 10 s")
    yield url
    server.shutdown()


@pytest.fixture(autouse=True)
def reset_app_state(base_url):
    """Every test starts from the seed data, so tests never depend on each other."""
    requests.post(f"{base_url}/api/test/reset", timeout=5).raise_for_status()


# -------------------------------------------------------------------- API
@pytest.fixture
def api(base_url) -> ApiClient:
    return ApiClient(base_url)


@pytest.fixture
def auth_api(api) -> ApiClient:
    response = api.login(**VALID_USER)
    assert response.status_code == 200, response.text
    return api.with_token(response.json()["token"])


# --------------------------------------------------------------------- UI
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    setattr(item, f"rep_{call.when}", outcome.get_result())


@pytest.fixture(scope="session")
def playwright_instance() -> Playwright:
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(playwright_instance: Playwright) -> Browser:
    """BROWSER_CHANNEL=chrome uses an installed Chrome instead of Playwright's Chromium.
    HEADED=1 shows the browser; SLOWMO=250 slows actions down for debugging."""
    launch_args = {
        "headless": os.getenv("HEADED") != "1",
        "slow_mo": int(os.getenv("SLOWMO", "0")),
    }
    if os.getenv("BROWSER_CHANNEL"):
        launch_args["channel"] = os.environ["BROWSER_CHANNEL"]
    browser = playwright_instance.chromium.launch(**launch_args)
    yield browser
    browser.close()


@pytest.fixture
def context(browser: Browser, base_url: str, playwright_instance: Playwright, request) -> BrowserContext:
    playwright_instance.selectors.set_test_id_attribute("data-test")
    context = browser.new_context(base_url=base_url, viewport={"width": 1280, "height": 800})
    context.set_default_timeout(5_000)
    context.tracing.start(screenshots=True, snapshots=True, sources=False)
    yield context
    failed = getattr(request.node, "rep_call", None) and request.node.rep_call.failed
    name = re.sub(r"[^\w.-]+", "_", request.node.nodeid)
    if failed:
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        context.tracing.stop(path=str(ARTIFACTS / f"{name}.trace.zip"))
    else:
        context.tracing.stop()
    context.close()


@pytest.fixture
def page(context: BrowserContext, request) -> Page:
    page = context.new_page()
    yield page
    failed = getattr(request.node, "rep_call", None) and request.node.rep_call.failed
    if failed:
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        name = re.sub(r"[^\w.-]+", "_", request.node.nodeid)
        page.screenshot(path=str(ARTIFACTS / f"{name}.png"), full_page=True)


@pytest.fixture
def logged_in_page(page: Page) -> Page:
    from tests.pages.login_page import LoginPage

    LoginPage(page).open().log_in(**VALID_USER)
    return page
