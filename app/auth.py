"""Demo authentication: scrypt password hashes (stdlib) and signed JWTs (PyJWT).

The user's group is read from the verified token only. It is never taken from a request body.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

N, R, P = 2**14, 8, 1
_DUMMY_HASH = None


class AuthError(Exception):
    """Invalid credentials or token."""


@dataclass(frozen=True)
class User:
    username: str
    group: str
    display_name: str


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=N, r=R, p=P, dklen=32)
    return f"scrypt${N}${R}${P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, expected = stored.split("$")
        if scheme != "scrypt":
            return False
        digest = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt), n=int(n),
                                r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(digest, base64.b64decode(expected))
    except (ValueError, TypeError):
        return False


def load_users(path: Path) -> dict[str, dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def authenticate(users: dict[str, dict], username: str, password: str) -> User:
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = hash_password("dummy")
    record = users.get(username)
    # Always hash, even for unknown users, so response time does not reveal valid usernames.
    ok = verify_password(password, record["password_hash"] if record else _DUMMY_HASH)
    if not record or not ok:
        raise AuthError("Invalid username or password")
    return User(username, record["group"], record.get("display_name", username))


def create_token(user: User, secret: str, algorithm: str, expire_minutes: int) -> str:
    import jwt

    now = int(time.time())
    payload = {"sub": user.username, "group": user.group, "name": user.display_name,
               "iat": now, "exp": now + expire_minutes * 60}
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_token(token: str, secret: str, algorithm: str, valid_groups: list[str]) -> User:
    import jwt

    try:
        payload = jwt.decode(token, secret, algorithms=[algorithm],
                             options={"require": ["exp", "sub", "group"]})
    except jwt.PyJWTError as exc:
        raise AuthError("Invalid or expired token") from exc
    if payload["group"] not in valid_groups:
        raise AuthError("Unknown group in token")
    return User(payload["sub"], payload["group"], payload.get("name", payload["sub"]))
