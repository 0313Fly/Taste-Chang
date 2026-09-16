"""用户打分与公共均分。"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
RATINGS_PATH = BASE_DIR / "data" / "ratings.json"
LEGACY_USER = "__legacy__"

_lock = threading.Lock()


def _read_ratings() -> dict[str, dict[str, float]]:
    if not RATINGS_PATH.exists():
        return {}
    with RATINGS_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {}
    out: dict[str, dict[str, float]] = {}
    for restaurant, votes in data.items():
        if not isinstance(votes, dict):
            continue
        cleaned: dict[str, float] = {}
        for user, score in votes.items():
            try:
                cleaned[str(user)] = round(float(score), 1)
            except (TypeError, ValueError):
                continue
        out[str(restaurant)] = cleaned
    return out


def _write_ratings(data: dict[str, dict[str, float]]) -> None:
    RATINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RATINGS_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def ensure_legacy_ratings(restaurants: list[dict]) -> None:
    """把历史 score 灌进 __legacy__，保证旧榜均分可延续。"""
    with _lock:
        data = _read_ratings()
        changed = False
        for item in restaurants:
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            votes = data.setdefault(name, {})
            if LEGACY_USER in votes:
                continue
            try:
                score = float(item.get("score"))
            except (TypeError, ValueError):
                continue
            votes[LEGACY_USER] = round(score, 1)
            changed = True
        if changed:
            _write_ratings(data)


def average_score(votes: dict[str, float] | None) -> tuple[float | None, int]:
    if not votes:
        return None, 0
    values = list(votes.values())
    avg = round(sum(values) / len(values), 1)
    return avg, len(values)


def get_restaurant_votes(restaurant: str) -> dict[str, float]:
    return dict(_read_ratings().get(restaurant) or {})


def get_user_score(restaurant: str, username: str) -> float | None:
    votes = get_restaurant_votes(restaurant)
    if username in votes:
        return votes[username]
    return None


def upsert_rating(*, restaurant: str, username: str, score: float) -> dict:
    """每位用户对每家店仅一条评分，可覆盖修改。"""
    score = round(float(score), 1)
    if score < 0 or score > 10:
        raise ValueError("评分须为 0–10")
    if username == LEGACY_USER:
        raise ValueError("非法用户")

    with _lock:
        data = _read_ratings()
        votes = data.setdefault(restaurant, {})
        votes[username] = score
        # 一旦有真实用户打分，可保留 legacy 一起平均
        _write_ratings(data)
        avg, n = average_score(votes)
        return {
            "restaurant": restaurant,
            "username": username,
            "my_score": score,
            "score": avg,
            "score_count": n,
            "updated_at": int(time.time()),
        }


def rename_restaurant_ratings(old_name: str, new_name: str) -> None:
    if old_name == new_name:
        return
    with _lock:
        data = _read_ratings()
        if old_name in data:
            existing = data.get(new_name) or {}
            merged = {**existing, **data.pop(old_name)}
            data[new_name] = merged
            _write_ratings(data)


def delete_restaurant_ratings(name: str) -> None:
    with _lock:
        data = _read_ratings()
        if name in data:
            data.pop(name)
            _write_ratings(data)


def attach_scores(items: list[dict], *, username: str | None = None) -> list[dict]:
    """为列表附加公共均分与当前用户评分。"""
    all_votes = _read_ratings()
    enriched = []
    for item in items:
        row = dict(item)
        name = str(row.get("name") or "")
        votes = all_votes.get(name) or {}
        avg, n = average_score(votes)
        if avg is None:
            # 兜底：尚无评分文件时用旧 score
            try:
                avg = round(float(row.get("score")), 1)
                n = 0
            except (TypeError, ValueError):
                avg = None
                n = 0
        row["score"] = avg
        row["score_count"] = n
        row["my_score"] = votes.get(username) if username else None
        enriched.append(row)
    return enriched
