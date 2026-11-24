"""JSON schemas for the API contract. Tests validate every response body
against these, so a renamed field or a wrong type fails loudly."""

PRODUCT = {
    "type": "object",
    "required": ["id", "name", "price", "category", "stock"],
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string", "minLength": 1},
        "price": {"type": "number", "exclusiveMinimum": 0},
        "category": {"enum": ["parts", "fluids", "tools"]},
        "stock": {"type": "integer", "minimum": 0},
    },
    "additionalProperties": False,
}

PRODUCT_LIST = {
    "type": "object",
    "required": ["items", "total", "limit", "offset"],
    "properties": {
        "items": {"type": "array", "items": PRODUCT},
        "total": {"type": "integer", "minimum": 0},
        "limit": {"type": "integer"},
        "offset": {"type": "integer"},
    },
}

ORDER = {
    "type": "object",
    "required": ["id", "user", "status", "items", "shipping", "total"],
    "properties": {
        "id": {"type": "integer"},
        "user": {"type": "string"},
        "status": {"enum": ["CREATED"]},
        "items": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["product_id", "name", "quantity", "unit_price"],
                "properties": {
                    "product_id": {"type": "integer"},
                    "name": {"type": "string"},
                    "quantity": {"type": "integer", "minimum": 1},
                    "unit_price": {"type": "number"},
                },
            },
        },
        "shipping": {
            "type": "object",
            "required": ["name", "postal_code"],
        },
        "total": {"type": "number", "exclusiveMinimum": 0},
    },
}

ORDER_LIST = {
    "type": "object",
    "required": ["items", "total"],
    "properties": {"items": {"type": "array", "items": ORDER}, "total": {"type": "integer"}},
}

LOGIN = {
    "type": "object",
    "required": ["token", "username"],
    "properties": {"token": {"type": "string", "minLength": 16}, "username": {"type": "string"}},
}

ERROR = {
    "type": "object",
    "required": ["error"],
    "properties": {"error": {"type": "string", "minLength": 1}},
}
