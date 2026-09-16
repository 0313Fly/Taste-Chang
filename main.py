"""常州美食排行榜 — Flask API + Vue 前端"""

from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, jsonify, render_template, request

DATA_PATH = Path(__file__).parent / "data" / "restaurants.json"
TITLE = "常州美食排行榜"

app = Flask(__name__)


def load_restaurants() -> list[dict]:
    with DATA_PATH.open(encoding="utf-8") as f:
        items = json.load(f)
    items.sort(key=lambda x: (x["score"], x["count"] or 0), reverse=True)
    return items


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/restaurants")
def api_restaurants():
    q = (request.args.get("q") or "").strip()
    items = load_restaurants()
    if q:
        items = [x for x in items if q.lower() in x["name"].lower()]
    return jsonify({"title": TITLE, "total": len(items), "items": items})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000, debug=False)
