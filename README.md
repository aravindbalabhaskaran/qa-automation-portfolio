# QA Automation Portfolio: Playwright, pytest and Postman

![tests](https://github.com/aravindbalabhaskaran/qa-automation-portfolio/actions/workflows/tests.yml/badge.svg)

End-to-end test automation for a small automotive-parts web shop. It covers the web UI and the REST API,
with the tests in Python (pytest) and the API checks also available as a Postman/Newman collection.

The shop (`demo_app/`) is a Flask app bundled in this repo, so everything runs offline, starts from the same seed data
every time, and needs no accounts or external sites.

| | |
|---|---|
| **UI tests** | Playwright (sync API) + pytest, page object model, role/label/test-id locators, no sleeps |
| **API tests** | `requests` + pytest, JSON Schema contract checks, status codes, side effects (stock) |
| **Postman** | Collection + environment with `pm.test` assertions, run by Newman in CI; a pytest test replays it so it cannot drift |
| **Cross-layer** | Buy in the browser, then verify the order and stock through the API |
| **CI** | GitHub Actions (`.github/workflows/tests.yml`) and a `Jenkinsfile` with JUnit reports |
| **Size** | 105 pytest tests (9 smoke; 33 browser tests, 75 API tests, 3 of them cross-layer and counted in both) + 19 Postman requests |

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium

pytest -m smoke        # about 9 tests, a few seconds
pytest                 # everything
pytest -m api          # no browser needed
pytest -m "ui and not e2e"
```

The suite starts the demo app on a free port by itself. To explore the app manually: `python -m demo_app`,
then open http://127.0.0.1:5000 (login `tester` / `Test@1234`; `locked_user` is a locked account).

### Postman / Newman

```bash
python -m demo_app &                                     # terminal 1
npx newman run postman/parts-shop.postman_collection.json \
    -e postman/local.postman_environment.json            # terminal 2
```
You can also import both files from `postman/` into the Postman app.

### Useful switches

| Variable | Effect |
|---|---|
| `HEADED=1` | show the browser |
| `SLOWMO=300` | slow every action by 300 ms to watch what happens |
| `BROWSER_CHANNEL=chrome` | use installed Chrome instead of Playwright's Chromium |
| `BASE_URL=https://...` | run against an already deployed environment instead of the bundled app |

When a UI test fails, a full-page screenshot and a Playwright trace are saved in `artifacts/`.
Open a trace with `playwright show-trace artifacts/<name>.trace.zip` to step through every action, DOM snapshot and network call.

## What is tested

* **Login:** valid user, wrong password, unknown user, empty fields, locked account, protected pages redirect, logout.
* **Catalogue:** search (case-insensitive, no results), sorting, out-of-stock handling, add-to-cart badge, and the API call the search triggers.
* **Cart and checkout:** totals, quantity merge, removal, empty cart, checkout validation, confirmation.
* **API:** auth, filtering, sorting, pagination boundaries, bad parameters, order creation/cancellation, stock changes, 401/404/405/409 behaviour.
* **Cross-layer:** order placed in the UI exists in the API with the right total; stock drops after checkout; UI search shows what the API returns.

More detail and the risk-based reasoning are in [`docs/test-plan.md`](docs/test-plan.md).

## Design choices

* **Independent tests.** An autouse fixture resets the app before every test, so any test can run alone or in any order.
* **No `sleep()`.** Playwright auto-waits; where the UI depends on a network call the test waits for that response explicitly (`page.expect_response`).
* **Page objects stay assertion-light.** They expose actions and locators; tests hold the assertions.
* **Parametrised negatives.** One test body, many inputs, with readable ids.
* **Contract checks.** Responses are validated against JSON Schemas in `tests/support/schemas.py`, so a renamed field fails loudly.
* **Markers.** `smoke` for every commit, `regression` for nightly, plus `ui`, `api`, `e2e`. `--strict-markers` catches typos.

## Layout

```
demo_app/              system under test (Flask): web UI + /api
tests/
  conftest.py          server, browser, tracing, API client fixtures
  pages/               page objects
  support/             API client, schemas, test data
  ui/  api/  e2e/      test files
postman/               collection + environment
docs/test-plan.md      scope, risks, coverage map, known gaps
```

## Limitations

Chromium only; no visual or accessibility checks; no load testing; in-memory state means one server per test run.
These are listed in the test plan on purpose.
