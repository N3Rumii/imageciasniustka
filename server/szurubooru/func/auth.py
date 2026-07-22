import hashlib
import secrets
import uuid
from collections import OrderedDict
from datetime import datetime
from typing import Optional, Tuple

import argon2

from szurubooru import config, db, errors, model
from szurubooru.func import util

RANK_MAP = OrderedDict(
    [
        (model.User.RANK_ANONYMOUS, "anonymous"),
        (model.User.RANK_RESTRICTED, "restricted"),
        (model.User.RANK_REGULAR, "regular"),
        (model.User.RANK_POWER, "power"),
        (model.User.RANK_MODERATOR, "moderator"),
        (model.User.RANK_ADMINISTRATOR, "administrator"),
        (model.User.RANK_NOBODY, "nobody"),
    ]
)


def get_password_hash(salt: str, password: str) -> Tuple[str, int]:
    """Retrieve argon2id password hash."""
    ph = argon2.PasswordHasher()
    return (
        ph.hash(
            (config.config["secret"] + salt + password).encode("utf8")
        ),
        3,
    )


def get_sha256_legacy_password_hash(
    salt: str, password: str
) -> Tuple[str, int]:
    """Retrieve old-style sha256 password hash."""
    digest = hashlib.sha256()
    digest.update(config.config["secret"].encode("utf8"))
    digest.update(salt.encode("utf8"))
    digest.update(password.encode("utf8"))
    return digest.hexdigest(), 2


def get_sha1_legacy_password_hash(salt: str, password: str) -> Tuple[str, int]:
    """Retrieve old-style sha1 password hash."""
    digest = hashlib.sha1()
    digest.update(b"1A2/$_4xVa")
    digest.update(salt.encode("utf8"))
    digest.update(password.encode("utf8"))
    return digest.hexdigest(), 1


def generate_password() -> str:
    """Generate a random password for auto-generated credentials."""
    return secrets.token_urlsafe(12)


def generate_salt() -> str:
    """Generate a cryptographically random salt (128 bits of entropy)."""
    return secrets.token_hex(16)


def is_valid_password(user: model.User, password: str) -> bool:
    assert user
    salt, valid_hash = user.password_salt, user.password_hash

    try:
        ph = argon2.PasswordHasher()
        return ph.verify(
            user.password_hash,
            (config.config["secret"] + salt + password).encode("utf8"),
        )
    except argon2.exceptions.VerifyMismatchError:
        possible_hashes = [
            get_sha256_legacy_password_hash(salt, password)[0],
            get_sha1_legacy_password_hash(salt, password)[0],
        ]
        if valid_hash in possible_hashes:
            # Convert the user password hash to the new hash
            new_hash, revision = get_password_hash(salt, password)
            user.password_hash = new_hash
            user.password_revision = revision
            db.session.commit()
            return True

    return False


def is_valid_token(user_token: Optional[model.UserToken]) -> bool:
    """
    Token must be enabled and if it has an expiration, it must be
    greater than now.
    """
    if user_token is None:
        return False
    if not user_token.enabled:
        return False
    if (
        user_token.expiration_time is not None
        and user_token.expiration_time < datetime.utcnow()
    ):
        return False
    return True


def has_privilege(user: model.User, privilege_name: str) -> bool:
    assert user
    all_ranks = list(RANK_MAP.keys())
    assert privilege_name in config.config["privileges"]
    assert user.rank in all_ranks
    minimal_rank = util.flip(RANK_MAP)[
        config.config["privileges"][privilege_name]
    ]
    good_ranks = all_ranks[all_ranks.index(minimal_rank) :]
    return user.rank in good_ranks


def verify_privilege(user: model.User, privilege_name: str) -> None:
    assert user
    if not has_privilege(user, privilege_name):
        raise errors.AuthError("Insufficient privileges to do this.")


def generate_authorization_token() -> str:
    return uuid.uuid4().__str__()
