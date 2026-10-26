"""Centralised application configuration.

Reads every tunable from the environment. Values that would be dangerous to
guess (the JWT signing key, the CORS allow-list) have **no fallback**: the
process refuses to start rather than run with an insecure default.

A `.env` file is loaded when present so local development keeps working
without exporting variables by hand; in Docker/EC2 the environment is
populated by docker-compose and the file is simply absent.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Project root: app/config.py -> app/ -> boscoGest/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env", override=False)


class ConfigurationError(RuntimeError):
    """Raised at import time when a mandatory setting is missing."""


def _required(name: str, hint: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigurationError(
            f"{name} is not set. {hint}"
        )
    return value


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def _int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    return int(raw) if raw else default


# ──────────────────────────────────────────────
# Security
# ──────────────────────────────────────────────

_INSECURE_SECRETS = {
    "your-secret-key-here",
    "your-super-secret-key-change-this-in-production-minimum-32-characters",
    "changeme",
    "secret",
}

SECRET_KEY = _required(
    "SECRET_KEY",
    "Generate one with `python -c \"import secrets; print(secrets.token_urlsafe(64))\"` "
    "and set it in the environment (or .env for local development).",
)

if SECRET_KEY in _INSECURE_SECRETS:
    raise ConfigurationError(
        "SECRET_KEY is set to a well-known placeholder value. Anyone reading the "
        "repository could forge valid tokens. Generate a real one with "
        '`python -c "import secrets; print(secrets.token_urlsafe(64))"`.'
    )

if len(SECRET_KEY) < 32:
    raise ConfigurationError(
        f"SECRET_KEY is only {len(SECRET_KEY)} characters long; use at least 32."
    )

ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = _int("ACCESS_TOKEN_EXPIRE_MINUTES", 30)

# Comma-separated allow-list. No wildcard fallback: `allow_credentials=True`
# together with `*` is rejected by browsers anyway and hides the mistake.
CORS_ORIGINS = [
    origin.strip()
    for origin in _required(
        "CORS_ORIGINS",
        "Set it to the comma-separated list of front-end origins, e.g. "
        "'https://app.example.org,http://localhost:4200'.",
    ).split(",")
    if origin.strip()
]

if "*" in CORS_ORIGINS:
    raise ConfigurationError(
        "CORS_ORIGINS contains '*', which cannot be combined with credentialed "
        "requests. List the front-end origins explicitly."
    )

# ──────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────

DATABASE_URL = _required(
    "DATABASE_URL",
    "Expected a SQLAlchemy URL such as "
    "'postgresql+psycopg2://user:password@host:5432/boscogest'.",
)

SQLALCHEMY_ECHO = _bool("SQLALCHEMY_ECHO", False)
DB_POOL_SIZE = _int("DB_POOL_SIZE", 20)
DB_MAX_OVERFLOW = _int("DB_MAX_OVERFLOW", 10)
DB_POOL_RECYCLE = _int("DB_POOL_RECYCLE", 1800)
DB_POOL_TIMEOUT = _int("DB_POOL_TIMEOUT", 30)

# ──────────────────────────────────────────────
# Storage
# ──────────────────────────────────────────────

STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "s3")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "")

# ──────────────────────────────────────────────
# Email (AWS SES)
# ──────────────────────────────────────────────

AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")
SES_SENDER_EMAIL = os.getenv("SES_SENDER_EMAIL", "")
SES_CONFIGURATION_SET = os.getenv("SES_CONFIGURATION_SET", "")
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:4200")

# ──────────────────────────────────────────────
# Notificaciones push (Firebase Cloud Messaging)
# ──────────────────────────────────────────────
#
# Sin credenciales el envío se salta con un aviso en el log, igual que el
# correo cuando falta SES_SENDER_EMAIL: la app funciona entera sin push, y el
# desarrollo local y los tests no necesitan un proyecto de Firebase.
#
# FCM_CREDENTIALS_FILE apunta al JSON de la cuenta de servicio que se descarga
# de la consola de Firebase. Nunca se sube al repositorio.

FCM_PROJECT_ID = os.getenv("FCM_PROJECT_ID", "")
FCM_CREDENTIALS_FILE = os.getenv("FCM_CREDENTIALS_FILE", "")


def push_is_configured() -> bool:
    """Si hay con qué enviar. Se consulta en cada envío, no al arrancar."""
    return bool(FCM_PROJECT_ID and FCM_CREDENTIALS_FILE)
