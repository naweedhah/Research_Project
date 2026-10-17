import json
import uuid

import jwt

from datetime import datetime, timedelta, timezone
from pwdlib import PasswordHash

from app.config import (
    USERS_FILE,
    AUTH_DATA_DIR,
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)


password_hash = PasswordHash.recommended()


def ensure_user_storage():
    AUTH_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not USERS_FILE.exists():
        with open(
            USERS_FILE,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump([], file)


def load_users():
    ensure_user_storage()

    with open(
        USERS_FILE,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def save_users(users):
    ensure_user_storage()

    with open(
        USERS_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            users,
            file,
            indent=2,
        )


def find_user_by_email(email: str):
    users = load_users()

    email_clean = email.strip().lower()

    for user in users:
        if user["email"].lower() == email_clean:
            return user

    return None


def register_user(
    name: str,
    email: str,
    password: str,
):
    email_clean = email.strip().lower()

    if find_user_by_email(email_clean):
        return None

    users = load_users()

    user = {
        "id": str(uuid.uuid4()),
        "name": name.strip(),
        "email": email_clean,
        "password_hash": password_hash.hash(
            password
        ),
        "created_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    users.append(user)

    save_users(users)

    return user


def authenticate_user(
    email: str,
    password: str,
):
    user = find_user_by_email(email)

    if not user:
        return None

    if not password_hash.verify(
        password,
        user["password_hash"],
    ):
        return None

    return user


def create_access_token(user):
    now = datetime.now(timezone.utc)

    expire = now + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": user["id"],
        "email": user["email"],
        "name": user["name"],
        "iat": now,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str):
    try:
        return jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )

    except jwt.PyJWTError:
        return None