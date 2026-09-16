"""常州美食排行榜 — Flask API（默认 8999）"""

from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, jsonify, request

BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "data" / "restaurants.json"
TITLE = "常州美食排行榜"
API_PORT = 8999

app = Flask(__name__)


def load_restaurants() -> list[dict]:
    with DATA_PATH.open(encoding="utf-8") as f:
        items = json.load(f)
    items.sort(key=lambda x: (x["score"], x["count"] or 0), reverse=True)
    return items


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    return response


@app.get("/")
def index():
    return jsonify(
        {
            "service": "Taste-Chang API",
            "port": API_PORT,
            "frontend": "http://127.0.0.1:9000",
            "api": "/api/restaurants",
        }
    )


@app.get("/api/restaurants")
def api_restaurants():
    q = (request.args.get("q") or "").strip()
    items = load_restaurants()
    if q:
        items = [x for x in items if q.lower() in x["name"].lower()]
    return jsonify({"title": TITLE, "total": len(items), "items": items})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=API_PORT, debug=False)
