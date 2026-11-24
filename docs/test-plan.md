# Test plan - Parts Shop demo

## Scope
Login, product browsing (search, sort), cart, checkout, and the REST API behind them.
Out of scope: payments, performance and load testing, accessibility audits.

## Approach
| Layer | Tool | Why |
|-------|------|-----|
| UI | Playwright + pytest, page objects | Auto-waiting avoids sleeps; locators use roles, labels and `data-test` ids |
| API | requests + pytest + JSON Schema | Fast, checks status codes, contract and side effects (stock) |
| API regression | Postman collection, run by Newman | Same checks in a format QA and developers already share |
| Cross-layer | pytest | Act in the browser, verify through the API |

Every test starts from seed data (`POST /api/test/reset`), so tests can run in any order.

## Risk-based priorities
1. **Money and stock:** wrong totals or stock drift lose money - covered by order total, stock decrement and restock-on-cancel tests.
2. **Access control:** protected endpoints and pages must reject anonymous users.
3. **Input validation:** quantities, postal code, malformed JSON, bad query parameters.
4. **Usability of search/sort:** empty state, case-insensitive search, correct ordering.

## Test levels
* `smoke` (9 tests): one happy path per feature, run on every commit.
* `regression`: negative cases, boundaries and parameterised data, run nightly.

## Coverage map
| Area | Test files |
|------|-----------|
| Authentication | `tests/ui/test_login.py`, `tests/api/test_auth_api.py` |
| Catalogue | `tests/ui/test_products.py`, `tests/api/test_products_api.py` |
| Cart and checkout | `tests/ui/test_cart_checkout.py` |
| Orders | `tests/api/test_orders_api.py`, `tests/e2e/test_ui_and_api.py` |
| Basic security | `tests/api/test_security_basics.py` |
| Postman sync | `tests/api/test_postman_collection.py` |

## Known gaps (honest list)
* Only Chromium is exercised; Firefox and WebKit are one line away in `conftest.py` but not run.
* No visual regression or accessibility checks.
* No load testing.
* The app keeps state in memory, so tests cannot run in parallel against one server.

## Bug report template
```
Title:        <short, specific>
Environment:  <build / URL / browser>
Steps:        1. ... 2. ...
Expected:     ...
Actual:       ...
Evidence:     <screenshot, trace zip, response body>
Severity:     <blocker | major | minor>
```
