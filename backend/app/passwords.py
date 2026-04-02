"""Argon2id password hashing and verification (with legacy plaintext upgrade path)."""
from __future__ import annotations

import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(stored: str, plain: str) -> tuple[bool, str | None]:
    """
    Returns (is_valid, new_hash_to_persist_or_none).
    new_hash is returned when upgrading from legacy plaintext or Argon2 parameters need rehashing.
    """
    if stored.startswith("$argon2"):
        try:
            _hasher.verify(stored, plain)
            if _hasher.check_needs_rehash(stored):
                return True, _hasher.hash(plain)
            return True, None
        except VerifyMismatchError:
            return False, None
    if secrets.compare_digest(stored, plain):
        return True, hash_password(plain)
    return False, None
