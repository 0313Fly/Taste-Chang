"""常州美食排行榜 — Flask API（默认 8999）"""

from __future__ import annotations

import json
import random
import threading
from collections import Counter
from pathlib import Path
from urllib.parse import unquote

from flask import Flask, jsonify, request

from auth import (
    authenticate,
    create_token,
    current_user,
    ensure_admin_user,
    register_user,
    require_admin,
    require_login,
)
from ratings import (
    attach_scores,
    delete_restaurant_ratings,
    ensure_legacy_ratings,
    rename_restaurant_ratings,
    upsert_rating,
)
from tagging import auto_tags, enrich_item

BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "data" / "restaurants.json"
TITLE = "常州美食排行榜"
API_PORT = 8999

app = Flask(__name__)
_lock = threading.Lock()

ensure_admin_user()


def read_raw_restaurants() -> list[dict]:
    with DATA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def write_raw_restaurants(items: list[dict]) -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(
        json.dumps(items, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_restaurants(*, username: str | None = None) -> list[dict]:
    raw = read_raw_restaurants()
    ensure_legacy_ratings(raw)
    items = [enrich_item(x) for x in raw]
    items = attach_scores(items, username=username)
    items.sort(
        key=lambda x: (
            x.get("score") is None,
            -(x.get("score") or 0),
            x.get("name") or "",
        )
    )
    return items


def parse_score(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    if score < 0 or score > 10:
        return None
    return round(score, 1)


def parse_tags(value: object, *, name: str) -> list[str]:
    tags: list[str] = []
    if isinstance(value, str):
        parts = [p.strip() for p in value.replace("，", ",").split(",")]
        tags = [p for p in parts if p]
    elif isinstance(value, list):
        tags = [str(t).strip() for t in value if str(t).strip()]
    seen: set[str] = set()
    uniq: list[str] = []
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            uniq.append(tag)
    if uniq:
        return uniq
    return auto_tags(name)


def find_index_by_name(items: list[dict], name: str) -> int:
    for i, item in enumerate(items):
        if item.get("name") == name:
            return i
    return -1


def pick_tonight(
    items: list[dict],
    *,
    n: int = 3,
    min_score: float = 7.0,
    tag: str = "",
) -> list[dict]:
    pool = [x for x in items if float(x.get("score") or 0) >= min_score]
    if tag:
        pool = [x for x in pool if tag in (x.get("tags") or [])]
    if not pool:
        pool = list(items)
        if tag:
            pool = [x for x in pool if tag in (x.get("tags") or [])]
    if not pool:
        return []

    weights = []
    for x in pool:
        score = float(x.get("score") or 0)
        weights.append(max(score ** 2, 0.01))

    k = min(n, len(pool))
    picks = []
    remaining = list(range(len(pool)))
    remaining_weights = weights[:]
    for _ in range(k):
        chosen = random.choices(remaining, weights=remaining_weights, k=1)[0]
        idx_in_remaining = remaining.index(chosen)
        picks.append(pool[chosen])
        remaining.pop(idx_in_remaining)
        remaining_weights.pop(idx_in_remaining)
        if not remaining:
            break
    return picks


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return response


@app.route("/api/<path:_any>", methods=["OPTIONS"])
def api_options(_any: str):
    return ("", 204)


@app.get("/")
def index():
    return jsonify(
        {
            "service": "Taste-Chang API",
            "port": API_PORT,
            "frontend": "http://127.0.0.1:9000",
            "api": "/api/restaurants",
            "auth": ["/api/register", "/api/login", "/api/me"],
            "rating": "PUT /api/restaurants/<name>/rating",
        }
    )


@app.post("/api/register")
def api_register():
    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username") or "").strip()
    password = str(payload.get("password") or "")
    user, err = register_user(username, password)
    if err:
        return jsonify({"error": err}), 400
    token = create_token(username=user["username"], role=user["role"])
    return jsonify({"ok": True, "token": token, "user": user}), 201


@app.post("/api/login")
def api_login():
    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username") or "").strip()
    password = str(payload.get("password") or "")
    user = authenticate(username, password)
    if not user:
        return jsonify({"error": "用户名或密码错误"}), 401
    token = create_token(username=user["username"], role=user["role"])
    return jsonify({"ok": True, "token": token, "user": user})


@app.get("/api/me")
def api_me():
    user = current_user()
    if not user:
        return jsonify({"authenticated": False, "user": None})
    return jsonify({"authenticated": True, "user": user})


@app.get("/api/tags")
@require_login
def api_tags():
    user = current_user()
    items = load_restaurants(username=user["username"] if user else None)
    counter: Counter[str] = Counter()
    for item in items:
        for tag in item.get("tags") or []:
            counter[tag] += 1
    tags = [{"tag": tag, "count": n} for tag, n in counter.most_common()]
    return jsonify({"total": len(tags), "tags": tags})


@app.get("/api/restaurants")
@require_login
def api_restaurants():
    user = current_user()
    q = (request.args.get("q") or "").strip()
    tag = (request.args.get("tag") or "").strip()
    items = load_restaurants(username=user["username"] if user else None)
    if q:
        items = [x for x in items if q.lower() in x["name"].lower()]
    if tag:
        items = [x for x in items if tag in (x.get("tags") or [])]
    return jsonify({"title": TITLE, "total": len(items), "items": items})


@app.post("/api/restaurants")
@require_admin
def api_create_restaurant():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name") or "").strip()
    if not name:
        return jsonify({"error": "店名不能为空"}), 400
    # 可选初始分：写入 legacy，参与公共均分
    init_score = parse_score(payload.get("score"))

    with _lock:
        items = read_raw_restaurants()
        if find_index_by_name(items, name) >= 0:
            return jsonify({"error": f"已存在同名饭店：{name}"}), 409
        item = {
            "name": name,
            "score": init_score if init_score is not None else 0,
            "tags": parse_tags(payload.get("tags"), name=name),
        }
        items.append(item)
        write_raw_restaurants(items)
        if init_score is not None:
            ensure_legacy_ratings([item])

    user = current_user()
    enriched = attach_scores([enrich_item(item)], username=user["username"] if user else None)[0]
    return jsonify({"ok": True, "item": enriched}), 201


@app.put("/api/restaurants")
@require_admin
def api_update_restaurant():
    payload = request.get_json(silent=True) or {}
    original_name = str(payload.get("original_name") or payload.get("name") or "").strip()
    name = str(payload.get("name") or "").strip()
    if not original_name:
        return jsonify({"error": "缺少 original_name"}), 400
    if not name:
        return jsonify({"error": "店名不能为空"}), 400

    with _lock:
        items = read_raw_restaurants()
        idx = find_index_by_name(items, original_name)
        if idx < 0:
            return jsonify({"error": f"未找到饭店：{original_name}"}), 404
        if name != original_name and find_index_by_name(items, name) >= 0:
            return jsonify({"error": f"已存在同名饭店：{name}"}), 409
        old = items[idx]
        item = {
            "name": name,
            "score": old.get("score", 0),
            "tags": parse_tags(payload.get("tags"), name=name),
        }
        items[idx] = item
        write_raw_restaurants(items)
        if name != original_name:
            rename_restaurant_ratings(original_name, name)

    user = current_user()
    enriched = attach_scores([enrich_item(item)], username=user["username"] if user else None)[0]
    return jsonify({"ok": True, "item": enriched})


@app.delete("/api/restaurants/<path:name>")
@require_admin
def api_delete_restaurant(name: str):
    name = unquote(name).strip()
    if not name:
        return jsonify({"error": "店名不能为空"}), 400
    with _lock:
        items = read_raw_restaurants()
        idx = find_index_by_name(items, name)
        if idx < 0:
            return jsonify({"error": f"未找到饭店：{name}"}), 404
        removed = items.pop(idx)
        write_raw_restaurants(items)
        delete_restaurant_ratings(name)
    return jsonify({"ok": True, "item": enrich_item(removed)})


@app.put("/api/restaurants/<path:name>/rating")
@require_login
def api_rate_restaurant(name: str):
    name = unquote(name).strip()
    user = current_user()
    assert user is not None
    payload = request.get_json(silent=True) or {}
    score = parse_score(payload.get("score"))
    if score is None:
        return jsonify({"error": "评分须为 0–10 的数字"}), 400

    with _lock:
        items = read_raw_restaurants()
        if find_index_by_name(items, name) < 0:
            return jsonify({"error": f"未找到饭店：{name}"}), 404
        try:
            result = upsert_rating(
                restaurant=name,
                username=user["username"],
                score=score,
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    return jsonify({"ok": True, **result})


@app.get("/api/tonight")
@require_login
def api_tonight():
    user = current_user()
    try:
        n = int(request.args.get("n") or 3)
    except ValueError:
        n = 3
    n = max(1, min(n, 5))
    try:
        min_score = float(request.args.get("min_score") or 7.0)
    except ValueError:
        min_score = 7.0
    tag = (request.args.get("tag") or "").strip()
    items = load_restaurants(username=user["username"] if user else None)
    picks = pick_tonight(items, n=n, min_score=min_score, tag=tag)
    return jsonify(
        {
            "title": "今晚吃什么",
            "total": len(picks),
            "min_score": min_score,
            "tag": tag or None,
            "items": picks,
            "hint": "按公共评分加权随机，分数越高越容易抽到",
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=API_PORT, debug=False)
