"""User registration service (TASK-082).

Handles:
- Password validation (>= 12 chars, 1 uppercase, 1 digit)
- Argon2 password hashing
- DEK generation and envelope encryption via Fernet + KEK
- User persistence with generic error on duplicate email (no email leak)
- JWT token pair issuance after successful registration

Security:
- Passwords are hashed with Argon2id (memory-hard, side-channel resistant).
- The per-user Data Encryption Key (DEK) is generated with os.urandom() and
  encrypted with the application KEK via Fernet before storage.
- Duplicate-email errors return a generic message to prevent enumeration.
"""

from __future__ import annotations

import base64
import logging
import os
import re
from typing import TYPE_CHECKING

from argon2 import PasswordHasher
from argon2.exceptions import HashingError, VerifyMismatchError
from cryptography.fernet import Fernet
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.exc import IntegrityError

from pwbs.core.config import get_settings
from pwbs.core.exceptions import AuthenticationError, ValidationError
from pwbs.models.user import User
from pwbs.services.auth import TokenPair, create_token_pair

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Argon2id hasher with recommended defaults
_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MiB
    parallelism=4,
    hash_len=32,
    salt_len=16,
)

# Password complexity requirements
_PASSWORD_MIN_LENGTH = 12
_PASSWORD_UPPERCASE_RE = re.compile(r"[A-Z]")
_PASSWORD_DIGIT_RE = re.compile(r"\d")


# ---------------------------------------------------------------------------
# Request schema
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    """Input schema for user registration."""

    model_config = ConfigDict(str_strip_whitespace=True)

    email: str
    password: str
    display_name: str

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        errors: list[str] = []
        if len(v) < _PASSWORD_MIN_LENGTH:
            errors.append(
                f"Passwort muss mindestens {_PASSWORD_MIN_LENGTH} Zeichen lang sein"
            )
        if not _PASSWORD_UPPERCASE_RE.search(v):
            errors.append("Passwort muss mindestens einen Großbuchstaben enthalten")
        if not _PASSWORD_DIGIT_RE.search(v):
            errors.append("Passwort muss mindestens eine Zahl enthalten")
        if errors:
            raise ValueError("; ".join(errors))
        return v

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Ungültiges E-Mail-Format")
        return v.lower()

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v: str) -> str:
        if not v or len(v.strip()) < 1:
            raise ValueError("Anzeigename darf nicht leer sein")
        return v


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


def hash_password(password: str) -> str:
    """Hash a password with Argon2id."""
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against an Argon2 hash.

    Returns True if the password matches, False otherwise.
    """
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


# ---------------------------------------------------------------------------
# DEK envelope encryption
# ---------------------------------------------------------------------------


def _generate_encrypted_dek() -> str:
    """Generate a per-user DEK and encrypt it with the application KEK.

    Returns the Fernet-encrypted DEK as a base64 string suitable for
    storage in `users.encryption_key_enc`.
    """
    settings = get_settings()
    kek = settings.encryption_master_key.get_secret_value()

    # Generate a fresh 32-byte DEK
    dek = os.urandom(32)

    # Derive a Fernet key from the KEK (pad/hash to 32 bytes for Fernet)
    import hashlib

    kek_bytes = hashlib.sha256(kek.encode("utf-8")).digest()
    fernet_key = base64.urlsafe_b64encode(kek_bytes)
    f = Fernet(fernet_key)

    # Encrypt the DEK
    encrypted_dek = f.encrypt(dek)
    return encrypted_dek.decode("utf-8")


# ---------------------------------------------------------------------------
# Registration service
# ---------------------------------------------------------------------------


async def register_user(
    data: RegisterRequest,
    db: AsyncSession,
) -> TokenPair:
    """Register a new user and return a JWT token pair.

    Raises:
        ValidationError: If password or email validation fails.
        AuthenticationError: With generic message if email is already taken
            (prevents email enumeration).
    """
    # Hash password
    try:
        password_hash = hash_password(data.password)
    except HashingError as exc:
        raise ValidationError(
            "Passwort-Hashing fehlgeschlagen",
            code="PASSWORD_HASH_ERROR",
        ) from exc

    # Generate encrypted DEK
    encryption_key_enc = _generate_encrypted_dek()

    # Create user
    user = User(
        email=data.email,
        display_name=data.display_name,
        password_hash=password_hash,
        encryption_key_enc=encryption_key_enc,
    )
    db.add(user)

    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        # Generic error message  do NOT reveal whether the email exists
        raise AuthenticationError(
            "Registrierung fehlgeschlagen",
            code="REGISTRATION_FAILED",
        )

    # Issue token pair
    pair = await create_token_pair(user.id, db)
    return pair
