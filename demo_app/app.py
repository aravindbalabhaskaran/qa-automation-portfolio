"""Small automotive-parts shop used as the system under test.

It exposes a server-rendered web UI (login, product search, cart, checkout)
and a JSON REST API. State lives in memory, so the app needs no database and
tests can reset it between runs through POST /api/test/reset.
"""
from __future__ import annotations

import copy
import secrets
import threading
from decimal import Decimal

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

USERS = {
    "tester": {"password": "Test@1234", "locked": False},
    "locked_user": {"password": "Test@1234", "locked": True},
}

# price is stored in cents to avoid float rounding errors in totals
_SEED_PRODUCTS = [
    {"id": 1, "name": "Brake Pad Set", "price_cents": 4990, "category": "parts", "stock": 25},
    {"id": 2, "name": "Engine Oil 5W-30", "price_cents": 3250, "category": "fluids", "stock": 40},
    {"id": 3, "name": "OBD-II Scanner", "price_cents": 7900, "category": "tools", "stock": 10},
    {"id": 4, "name": "Digital Multimeter", "price_cents": 2499, "category": "tools", "stock": 0},
    {"id": 5, "name": "Tyre Pressure Gauge", "price_cents": 1290, "category": "tools", "stock": 60},
    {"id": 6, "name": "LED Headlight Bulb", "price_cents": 1875, "category": "parts", "stock": 33},
]

SORTS = {
    "name": lambda p: p["name"].lower(),
    "price_asc": lambda p: p["price_cents"],
    "price_desc": lambda p: -p["price_cents"],
}
MAX_QTY_PER_LINE = 10

_lock = threading.RLock()
_state: dict = {}


def reset_state() -> None:
    with _lock:
        _state["products"] = copy.deepcopy(_SEED_PRODUCTS)
        _state["orders"] = {}
        _state["tokens"] = {}
        _state["next_order_id"] = 1


reset_state()


def _public_product(p: dict) -> dict:
    return {
        "id": p["id"],
        "name": p["name"],
        "price": p["price_cents"] / 100,
        "category": p["category"],
        "stock": p["stock"],
    }


def _find_product(product_id: int) -> dict | None:
    return next((p for p in _state["products"] if p["id"] == product_id), None)


class OrderError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def create_order(username: str, items: list, shipping: dict) -> dict:
    """Validate and create an order. Shared by the API and the web checkout."""
    if not isinstance(items, list) or not items:
        raise OrderError(400, "items must be a non-empty list")
    if not isinstance(shipping, dict):
        raise OrderError(400, "shipping is required")
    name = str(shipping.get("name", "")).strip()
    postal = str(shipping.get("postal_code", "")).strip()
    if not name:
        raise OrderError(400, "shipping.name is required")
    if not (postal.isdigit() and len(postal) == 5):
        raise OrderError(400, "shipping.postal_code must be 5 digits")

    wanted: dict[int, int] = {}
    for item in items:
        if not isinstance(item, dict):
            raise OrderError(400, "each item must be an object")
        pid, qty = item.get("product_id"), item.get("quantity")
        if isinstance(pid, bool) or not isinstance(pid, int):
            raise OrderError(400, "product_id must be an integer")
        if isinstance(qty, bool) or not isinstance(qty, int) or not 1 <= qty <= MAX_QTY_PER_LINE:
            raise OrderError(400, f"quantity must be an integer between 1 and {MAX_QTY_PER_LINE}")
        wanted[pid] = wanted.get(pid, 0) + qty

    with _lock:
        lines, total_cents = [], 0
        for pid, qty in wanted.items():
            product = _find_product(pid)
            if product is None:
                raise OrderError(404, f"Product {pid} not found")
            if product["stock"] == 0:
                raise OrderError(409, f"{product['name']} is out of stock")
            if qty > product["stock"]:
                raise OrderError(409, f"Only {product['stock']} left of {product['name']}")
            lines.append((product, qty))
            total_cents += product["price_cents"] * qty
        for product, qty in lines:
            product["stock"] -= qty
        order_id = _state["next_order_id"]
        _state["next_order_id"] += 1
        order = {
            "id": order_id,
            "user": username,
            "status": "CREATED",
            "items": [
                {"product_id": p["id"], "name": p["name"], "quantity": q, "unit_price": p["price_cents"] / 100}
                for p, q in lines
            ],
            "shipping": {"name": name, "postal_code": postal},
            "total": float(Decimal(total_cents) / 100),
        }
        _state["orders"][order_id] = order
        return copy.deepcopy(order)


def create_app(enable_test_endpoints: bool = True) -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = secrets.token_hex(16)

    # ------------------------------------------------------------------ helpers
    def json_error(status: int, message: str):
        return jsonify({"error": message}), status

    def current_api_user():
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return None
        return _state["tokens"].get(header[len("Bearer "):])

    def cart_items():
        cart = session.get("cart", {})
        rows = []
        for pid, qty in cart.items():
            product = _find_product(int(pid))
            if product:
                rows.append({"product": product, "quantity": qty, "line_cents": product["price_cents"] * qty})
        return rows

    @app.context_processor
    def inject_globals():
        return {
            "user": session.get("user"),
            "cart_count": sum(session.get("cart", {}).values()),
            "euro": lambda cents: f"€{cents / 100:.2f}",
        }

    # --------------------------------------------------------------- JSON API
    @app.errorhandler(404)
    def not_found(_):
        if request.path.startswith("/api/"):
            return json_error(404, "Not found")
        return render_template("message.html", title="Page not found"), 404

    @app.errorhandler(405)
    def method_not_allowed(_):
        return json_error(405, "Method not allowed")

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/api/auth/login")
    def api_login():
        data = request.get_json(silent=True) or {}
        username, password = data.get("username"), data.get("password")
        if not username or not password:
            return json_error(400, "username and password are required")
        account = USERS.get(username)
        if account is None or account["password"] != password:
            return json_error(401, "Invalid username or password")
        if account["locked"]:
            return json_error(403, "This account is locked")
        token = secrets.token_hex(16)
        _state["tokens"][token] = username
        return jsonify({"token": token, "username": username})

    @app.get("/api/products")
    def api_products():
        q = request.args.get("q", "").strip().lower()
        category = request.args.get("category")
        sort = request.args.get("sort", "name")
        if sort not in SORTS:
            return json_error(400, f"sort must be one of {sorted(SORTS)}")
        try:
            limit = int(request.args.get("limit", 50))
            offset = int(request.args.get("offset", 0))
        except ValueError:
            return json_error(400, "limit and offset must be integers")
        if not 1 <= limit <= 50 or offset < 0:
            return json_error(400, "limit must be 1-50 and offset must be >= 0")
        with _lock:
            items = [p for p in _state["products"] if q in p["name"].lower()]
            if category:
                items = [p for p in items if p["category"] == category]
            items.sort(key=SORTS[sort])
            page = [_public_product(p) for p in items[offset: offset + limit]]
        return jsonify({"items": page, "total": len(items), "limit": limit, "offset": offset})

    @app.get("/api/products/<int:product_id>")
    def api_product(product_id: int):
        with _lock:
            product = _find_product(product_id)
            if product is None:
                return json_error(404, "Product not found")
            return jsonify(_public_product(product))

    @app.post("/api/orders")
    def api_create_order():
        user = current_api_user()
        if not user:
            return json_error(401, "Authentication required")
        data = request.get_json(silent=True) or {}
        try:
            order = create_order(user, data.get("items"), data.get("shipping"))
        except OrderError as err:
            return json_error(err.status, err.message)
        return jsonify(order), 201

    @app.get("/api/orders")
    def api_list_orders():
        user = current_api_user()
        if not user:
            return json_error(401, "Authentication required")
        with _lock:
            mine = [o for o in _state["orders"].values() if o["user"] == user]
        return jsonify({"items": mine, "total": len(mine)})

    @app.get("/api/orders/<int:order_id>")
    def api_get_order(order_id: int):
        user = current_api_user()
        if not user:
            return json_error(401, "Authentication required")
        order = _state["orders"].get(order_id)
        if order is None or order["user"] != user:
            return json_error(404, "Order not found")
        return jsonify(order)

    @app.delete("/api/orders/<int:order_id>")
    def api_cancel_order(order_id: int):
        user = current_api_user()
        if not user:
            return json_error(401, "Authentication required")
        with _lock:
            order = _state["orders"].get(order_id)
            if order is None or order["user"] != user:
                return json_error(404, "Order not found")
            for line in order["items"]:
                _find_product(line["product_id"])["stock"] += line["quantity"]
            del _state["orders"][order_id]
        return "", 204

    if enable_test_endpoints:
        @app.post("/api/test/reset")
        def api_reset():
            reset_state()
            return "", 204

    # ------------------------------------------------------------------ web UI
    @app.get("/")
    def index():
        return redirect(url_for("products" if session.get("user") else "login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        error = None
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            account = USERS.get(username)
            if not username or not password:
                error = "Username and password are required"
            elif account is None or account["password"] != password:
                error = "Invalid username or password"
            elif account["locked"]:
                error = "This account is locked"
            else:
                session["user"] = username
                session["cart"] = {}
                return redirect(url_for("products"))
        return render_template("login.html", error=error), (401 if error else 200)

    @app.get("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.get("/products")
    def products():
        if not session.get("user"):
            return redirect(url_for("login"))
        return render_template("products.html")

    @app.post("/cart/add")
    def cart_add():
        if not session.get("user"):
            return json_error(401, "Authentication required")
        data = request.get_json(silent=True) or {}
        pid = data.get("product_id")
        product = _find_product(pid) if isinstance(pid, int) else None
        if product is None:
            return json_error(404, "Product not found")
        if product["stock"] == 0:
            return json_error(409, "Out of stock")
        cart = session.get("cart", {})
        cart[str(pid)] = min(cart.get(str(pid), 0) + 1, min(MAX_QTY_PER_LINE, product["stock"]))
        session["cart"] = cart
        return jsonify({"count": sum(cart.values())})

    @app.get("/cart")
    def cart():
        if not session.get("user"):
            return redirect(url_for("login"))
        rows = cart_items()
        return render_template("cart.html", rows=rows, total_cents=sum(r["line_cents"] for r in rows))

    @app.post("/cart/remove/<int:product_id>")
    def cart_remove(product_id: int):
        cart = session.get("cart", {})
        cart.pop(str(product_id), None)
        session["cart"] = cart
        return redirect(url_for("cart"))

    @app.route("/checkout", methods=["GET", "POST"])
    def checkout():
        if not session.get("user"):
            return redirect(url_for("login"))
        rows = cart_items()
        if not rows:
            return redirect(url_for("cart"))
        error = None
        if request.method == "POST":
            shipping = {
                "name": request.form.get("name", ""),
                "postal_code": request.form.get("postal_code", ""),
            }
            items = [{"product_id": r["product"]["id"], "quantity": r["quantity"]} for r in rows]
            try:
                order = create_order(session["user"], items, shipping)
            except OrderError as err:
                error = err.message
            else:
                session["cart"] = {}
                return render_template("confirmation.html", order=order)
        return render_template("checkout.html", error=error), (400 if error else 200)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
