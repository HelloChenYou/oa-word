import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.models import UserAccount


UserRole = Literal["admin", "operator"]


def _urlsafe_b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _urlsafe_b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _sign(value: str) -> str:
    return _urlsafe_b64encode(
        hmac.new(settings.auth_secret_key.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).digest()
    )


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt, digest = password_hash.split("$", 1)
    except ValueError:
        return False
    expected_hash = hash_password(password, salt)
    return hmac.compare_digest(expected_hash, password_hash)


def create_access_token(username: str, role: str, must_change_password: bool = False) -> str:
    payload = {
        "sub": username,
        "role": role,
        "must_change_password": must_change_password,
        "exp": int((datetime.now(timezone.utc) + timedelta(seconds=settings.auth_token_expire_sec)).timestamp()),
    }
    payload_raw = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    signature = _sign(payload_raw)
    return f"{_urlsafe_b64encode(payload_raw.encode('utf-8'))}.{signature}"


def decode_access_token(token: str) -> dict:
    try:
        payload_b64, signature = token.split(".", 1)
        payload_raw = _urlsafe_b64decode(payload_b64).decode("utf-8")
    except Exception as exc:
        raise HTTPException(status_code=401, detail="invalid token") from exc

    if not hmac.compare_digest(_sign(payload_raw), signature):
        raise HTTPException(status_code=401, detail="invalid token")

    payload = json.loads(payload_raw)
    if payload.get("exp", 0) < int(datetime.now(timezone.utc).timestamp()):
        raise HTTPException(status_code=401, detail="token expired")
    return payload


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def _build_user_identity(username: str, role: str, must_change_password: bool = False) -> dict:
    return {"username": username, "role": role, "must_change_password": must_change_password}


def bootstrap_admin_user() -> None:
    if not settings.bootstrap_admin_username.strip() or not settings.bootstrap_admin_password.strip():
        return

    db = SessionLocal()
    try:
        existing = db.execute(
            select(UserAccount).where(UserAccount.username == settings.bootstrap_admin_username)
        ).scalar_one_or_none()
        if existing is not None:
            return
        db.add(
            UserAccount(
                username=settings.bootstrap_admin_username,
                password_hash=hash_password(settings.bootstrap_admin_password),
                role="admin",
                enabled=True,
                must_change_password=True,
            )
        )
        db.commit()
    finally:
        db.close()


def authenticate_user(username: str, password: str) -> dict | None:
    db = SessionLocal()
    try:
        user = db.execute(select(UserAccount).where(UserAccount.username == username)).scalar_one_or_none()
        if user is None or not user.enabled:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return _build_user_identity(user.username, user.role, user.must_change_password)
    finally:
        db.close()


def get_current_user(
    authorization: str | None = Header(default=None),
    x_admin_token: str | None = Header(default=None),
) -> dict:
    header_value = x_admin_token if isinstance(x_admin_token, str) else None
    bearer_value = authorization if isinstance(authorization, str) else None

    if settings.admin_auth_enabled and header_value == settings.admin_api_token:
        return _build_user_identity("admin-token", "admin", False)

    token = _extract_bearer_token(bearer_value)
    if not token:
        raise HTTPException(status_code=401, detail="unauthorized")

    payload = decode_access_token(token)
    return _build_user_identity(payload["sub"], payload["role"], bool(payload.get("must_change_password", False)))


def require_authenticated(current_user: dict = Depends(get_current_user)) -> dict:
    return current_user


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="forbidden")
    return current_user


def change_user_password(username: str, current_password: str, new_password: str) -> dict | None:
    db = SessionLocal()
    try:
        user = db.execute(select(UserAccount).where(UserAccount.username == username)).scalar_one_or_none()
        if user is None or not user.enabled:
            return None
        if not verify_password(current_password, user.password_hash):
            return None
        user.password_hash = hash_password(new_password)
        user.must_change_password = False
        db.commit()
        return _build_user_identity(user.username, user.role, user.must_change_password)
    finally:
        db.close()


def list_users() -> list[UserAccount]:
    db = SessionLocal()
    try:
        return db.execute(select(UserAccount).order_by(UserAccount.created_at.asc())).scalars().all()
    finally:
        db.close()


def create_user_account(
    username: str,
    password: str,
    role: str,
    enabled: bool = True,
    must_change_password: bool = True,
) -> UserAccount | None:
    db = SessionLocal()
    try:
        existing = db.execute(select(UserAccount).where(UserAccount.username == username)).scalar_one_or_none()
        if existing is not None:
            return None
        user = UserAccount(
            username=username,
            password_hash=hash_password(password),
            role=role,
            enabled=enabled,
            must_change_password=must_change_password,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def update_user_account(
    username: str,
    *,
    role: str | None = None,
    enabled: bool | None = None,
    must_change_password: bool | None = None,
) -> UserAccount | None:
    db = SessionLocal()
    try:
        user = db.execute(select(UserAccount).where(UserAccount.username == username)).scalar_one_or_none()
        if user is None:
            return None
        if role is not None:
            user.role = role
        if enabled is not None:
            user.enabled = enabled
        if must_change_password is not None:
            user.must_change_password = must_change_password
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def reset_user_password(username: str, new_password: str, must_change_password: bool = True) -> UserAccount | None:
    db = SessionLocal()
    try:
        user = db.execute(select(UserAccount).where(UserAccount.username == username)).scalar_one_or_none()
        if user is None:
            return None
        user.password_hash = hash_password(new_password)
        user.must_change_password = must_change_password
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()
