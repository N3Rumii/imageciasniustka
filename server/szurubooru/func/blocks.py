"""User blocking business logic."""

import logging
from datetime import datetime
from typing import List, Optional

import sqlalchemy as sa

from szurubooru import db, errors, model

logger = logging.getLogger(__name__)


class BlockError(errors.ValidationError):
    pass


def _table_exists() -> bool:
    """Check if user_block table exists (migration may not have run yet)."""
    try:
        db.session.execute(sa.text("SELECT 1 FROM user_block LIMIT 0"))
        return True
    except Exception:
        return False


def block_user(
    blocker: model.User, blocked: model.User
) -> model.UserBlock:
    """Block a user. Returns the block record."""
    assert blocker and blocker.user_id
    assert blocked and blocked.user_id

    if not _table_exists():
        raise BlockError("Blocking is not available yet (pending migration).")

    if blocker.user_id == blocked.user_id:
        raise BlockError("You cannot block yourself.")

    existing = (
        db.session.query(model.UserBlock)
        .filter(
            model.UserBlock.blocker_id == blocker.user_id,
            model.UserBlock.blocked_id == blocked.user_id,
        )
        .one_or_none()
    )
    if existing:
        raise BlockError("User %r is already blocked." % blocked.name)

    block = model.UserBlock()
    block.blocker_id = blocker.user_id
    block.blocked_id = blocked.user_id
    block.creation_time = datetime.utcnow()
    db.session.add(block)

    # Also delete any existing conversation between them
    from szurubooru.func import chat as chat_mod
    try:
        chat_mod.delete_conversation(blocker, blocked.name)
    except Exception:
        pass

    return block


def unblock_user(blocker: model.User, blocked: model.User) -> None:
    """Unblock a user."""
    assert blocker and blocker.user_id
    assert blocked and blocked.user_id

    if not _table_exists():
        raise BlockError("Blocking is not available yet (pending migration).")

    existing = (
        db.session.query(model.UserBlock)
        .filter(
            model.UserBlock.blocker_id == blocker.user_id,
            model.UserBlock.blocked_id == blocked.user_id,
        )
        .one_or_none()
    )
    if not existing:
        raise BlockError("User %r is not blocked." % blocked.name)

    db.session.delete(existing)


def is_blocked_by(blocker_id: int, blocked_id: int) -> bool:
    """Check if blocker has blocked blocked."""
    if not _table_exists():
        return False
    try:
        return (
            db.session.query(model.UserBlock)
            .filter(
                model.UserBlock.blocker_id == blocker_id,
                model.UserBlock.blocked_id == blocked_id,
            )
            .one_or_none()
            is not None
        )
    except Exception:
        return False


def is_blocked_either_way(user1_id: int, user2_id: int) -> bool:
    """Check if either user has blocked the other."""
    return is_blocked_by(user1_id, user2_id) or is_blocked_by(
        user2_id, user1_id
    )


def get_blocked_user_ids(blocker_id: int) -> List[int]:
    """Return list of user IDs blocked by blocker."""
    if not _table_exists():
        return []
    try:
        rows = (
            db.session.query(model.UserBlock.blocked_id)
            .filter(model.UserBlock.blocker_id == blocker_id)
            .all()
        )
        return [r[0] for r in rows]
    except Exception:
        return []


def get_blocked_users(blocker: model.User) -> List[model.User]:
    """Return list of User objects blocked by blocker."""
    blocked_ids = get_blocked_user_ids(blocker.user_id)
    if not blocked_ids:
        return []
    return (
        db.session.query(model.User)
        .filter(model.User.user_id.in_(blocked_ids))
        .all()
    )


def should_strip_css(viewer: Optional[model.User], profile_user: model.User) -> bool:
    """Whether to strip custom CSS from profile_user when viewed by viewer.
    CSS is stripped if viewer has blocked profile_user OR profile_user has blocked viewer.
    """
    if not viewer or not viewer.user_id:
        return False
    return is_blocked_either_way(viewer.user_id, profile_user.user_id)
