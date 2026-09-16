"""常州美食排行榜 — Flask API（默认 8999）"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from flask import Flask, jsonify, request

from tagging import enrich_item

BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "data" / "restaurants.json"
TITLE = "常州美食排行榜"
API_PORT = 8999

app = Flask(__name__)


def load_restaurants() -> list[dict]:
    with DATA_PATH.open(encoding="utf-8") as f:
        items = json.load(f)
    items = [enrich_item(x) for x in items]
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
            "tags": "/api/tags",
        }
    )


@app.get("/api/tags")
def api_tags():
    items = load_restaurants()
    counter: Counter[str] = Counter()
    for item in items:
        for tag in item.get("tags") or []:
            counter[tag] += 1
    tags = [{"tag": tag, "count": n} for tag, n in counter.most_common()]
    return jsonify({"total": len(tags), "tags": tags})


@app.get("/api/restaurants")
def api_restaurants():
    q = (request.args.get("q") or "").strip()
    tag = (request.args.get("tag") or "").strip()
    items = load_restaurants()
    if q:
        items = [x for x in items if q.lower() in x["name"].lower()]
    if tag:
        items = [x for x in items if tag in (x.get("tags") or [])]
    return jsonify({"title": TITLE, "total": len(items), "items": items})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=API_PORT, debug=False)
