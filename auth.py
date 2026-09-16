"""用户注册 / 登录与 Token 校验。"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import threading
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from functools import wraps
from pathlib import Path
from typing import Any, Callable

from flask import jsonify, request

BASE_DIR = Path(__file__).resolve().parent
USERS_PATH = BASE_DIR / "data" / "users.json"

ADMIN_USERNAME = os.getenv("TASTE_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("TASTE_ADMIN_PASSWORD", "changzhou")
AUTH_SECRET = os.getenv("TASTE_AUTH_SECRET", "taste-chang-dev-secret-change-me")
TOKEN_TTL_SEC = int(os.getenv("TASTE_TOKEN_TTL", str(7 * 24 * 3600)))

_USERNAME_RE = re.compile(r"^[A-Za-z0-9_\u4e00-\u9fff]{2,20}$")
_lock = threading.Lock()


def _b64encode(raw: bytes) -> str:
    return urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return urlsafe_b64decode(text + pad)


def hash_password(password: str, *, salt: str | None = None) -> str:
    if salt is None:
        salt = _b64encode(os.urandom(16))
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120_000,
    )
    return f"{salt}${_b64encode(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, _ = stored.split("$", 1)
    except ValueError:
        return False
    return hmac.compare_digest(hash_password(password, salt=salt), stored)


def create_token(*, username: str, role: str) -> str:
    payload = {
        "u": username,
        "r": role,
        "exp": int(time.time()) + TOKEN_TTL_SEC,
    }
    body = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = _b64encode(
        hmac.new(AUTH_SECRET.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    )
    return f"{body}.{sig}"


def verify_token(token: str | None) -> dict[str, Any] | None:
    if not token or "." not in token:
        return None
    body, sig = token.rsplit(".", 1)
    expect = _b64encode(
        hmac.new(AUTH_SECRET.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    )
    if not hmac.compare_digest(sig, expect):
        return None
    try:
        payload = json.loads(_b64decode(body).decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if int(payload.get("exp") or 0) < int(time.time()):
        return None
    return payload


def _read_users() -> list[dict]:
    if not USERS_PATH.exists():
        return []
    with USERS_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def _write_users(users: list[dict]) -> None:
    USERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    USERS_PATH.write_text(
        json.dumps(users, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def ensure_admin_user() -> None:
    """确保内置管理员账号存在（密码以当前环境变量为准）。"""
    with _lock:
        users = _read_users()
        idx = next((i for i, u in enumerate(users) if u.get("username") == ADMIN_USERNAME), -1)
        admin_row = {
            "username": ADMIN_USERNAME,
            "password_hash": hash_password(ADMIN_PASSWORD),
            "role": "admin",
            "created_at": int(time.time()),
        }
        if idx < 0:
            users.append(admin_row)
        else:
            # 保留原创建时间，刷新密码哈希与角色
            admin_row["created_at"] = users[idx].get("created_at") or admin_row["created_at"]
            users[idx] = admin_row
        _write_users(users)


def find_user(username: str) -> dict | None:
    for user in _read_users():
        if user.get("username") == username:
            return user
    return None


def validate_username(username: str) -> str | None:
    if not _USERNAME_RE.match(username):
        return "用户名为 2–20 位中英文/数字/下划线"
    return None


def register_user(username: str, password: str) -> tuple[dict | None, str | None]:
    username = username.strip()
    err = validate_username(username)
    if err:
        return None, err
    if len(password) < 6:
        return None, "密码至少 6 位"
    if username == ADMIN_USERNAME:
        return None, "该用户名为系统保留，请换一个"

    with _lock:
        users = _read_users()
        if any(u.get("username") == username for u in users):
            return None, "用户名已存在"
        user = {
            "username": username,
            "password_hash": hash_password(password),
            "role": "user",
            "created_at": int(time.time()),
        }
        users.append(user)
        _write_users(users)
    return {"username": username, "role": "user"}, None


def authenticate(username: str, password: str) -> dict | None:
    user = find_user(username.strip())
    if not user:
        return None
    if not verify_password(password, str(user.get("password_hash") or "")):
        return None
    return {"username": user["username"], "role": user.get("role") or "user"}


def get_bearer_token() -> str | None:
    auth = request.headers.get("Authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    return None


def current_user() -> dict[str, Any] | None:
    payload = verify_token(get_bearer_token())
    if not payload:
        return None
    return {"username": payload.get("u"), "role": payload.get("r") or "user"}


def current_admin() -> dict[str, Any] | None:
    user = current_user()
    if not user or user.get("role") != "admin":
        return None
    return user


def require_login(view: Callable):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            return jsonify({"error": "请先登录"}), 401
        return view(*args, **kwargs)

    return wrapped


def require_admin(view: Callable):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_admin():
            return jsonify({"error": "需要管理员权限"}), 401
        return view(*args, **kwargs)

    return wrapped
