"""
Authentication and Password Security Utilities for PayRoute AI.
Provides cryptographic password hashing using PBKDF2-HMAC-SHA256 with random salt.
"""

import hashlib
import os
import secrets
from typing import Tuple


def hash_password(password: str, salt: str = None) -> str:
    """
    Hashes a plaintext password using PBKDF2-HMAC-SHA256 with 100,000 iterations.

    Args:
        password: Plaintext password string.
        salt: Optional 32-character hex salt. If None, generates a cryptographically secure salt.

    Returns:
        Formatted string: "{salt}${hash}"
    """
    if salt is None:
        salt = secrets.token_hex(16)  # 16 bytes = 32 hex chars

    iterations = 100_000
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    hash_hex = hash_bytes.hex()
    return f"{salt}${hash_hex}"


def verify_password(password: str, stored_hash: str) -> bool:
    """
    Verifies a plaintext password against a stored "{salt}${hash}" string using constant-time comparison.

    Args:
        password: Plaintext candidate password.
        stored_hash: Stored formatted hash string.

    Returns:
        True if password matches, False otherwise.
    """
    if not stored_hash or "$" not in stored_hash:
        return False

    try:
        salt, expected_hash = stored_hash.split("$", 1)
        calculated_entry = hash_password(password, salt=salt)
        _, calculated_hash = calculated_entry.split("$", 1)
        return secrets.compare_digest(expected_hash, calculated_hash)
    except Exception:
        return False
