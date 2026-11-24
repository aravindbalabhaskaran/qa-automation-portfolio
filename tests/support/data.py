"""Test data shared by UI and API tests."""

VALID_USER = {"username": "tester", "password": "Test@1234"}
LOCKED_USER = {"username": "locked_user", "password": "Test@1234"}

SHIPPING = {"name": "Aravind B", "postal_code": "12459"}

# Product ids from the seed data in demo_app/app.py
BRAKE_PADS = 1          # 49.90, stock 25
ENGINE_OIL = 2          # 32.50, stock 40
OBD_SCANNER = 3         # 79.00, stock 10
OUT_OF_STOCK = 4        # Digital Multimeter, stock 0
TYRE_GAUGE = 5          # 12.90, stock 60
