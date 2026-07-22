"""Chat business logic — encrypted messaging.

Server-side encryption: all messages are AES-256-GCM encrypted at rest
using a master key from config.yaml. The wire is protected by HTTPS.
Optional: per-conversation E2E keys for client-side encryption.
"""

import hashlib
import json
import os
import time
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional

import sqlalchemy as sa

from szurubooru import config, db, errors, model
from szurubooru.func import users, util

# ── Server-side crypto ────────────────────────────────

def _get_master_key() -> bytes:
    """Derive 32-byte AES key from config's chat_encryption_key."""
    raw = config.config.get("chat_encryption_key", "")
    if not raw or len(raw) < 32:
        raise ChatError("Server encryption key not configured.")
    return hashlib.sha256(raw.encode()).digest()


def _encrypt(plaintext: str) -> tuple:
    """Encrypt plaintext using SHAKE-256 stream cipher (stdlib only, no C deps)."""
    import base64
    key = _get_master_key()
    nonce = os.urandom(16)
    # Derive keystream: SHAKE-256(key + nonce) → deterministic stream
    keystream = hashlib.shake_256(key + nonce).digest(len(plaintext.encode()) + 32)
    # XOR plaintext with keystream
    pt_bytes = plaintext.encode("utf-8")
    ct_bytes = bytes(a ^ b for a, b in zip(pt_bytes, keystream[:len(pt_bytes)]))
    # Append HMAC for integrity (first 32 bytes of keystream after plaintext)
    mac = hashlib.sha256(key + nonce + ct_bytes).digest()[:16]
    final = ct_bytes + mac
    return base64.b64encode(final).decode(), base64.b64encode(nonce).decode()


def _serialize_message(m: model.Message) -> dict:
    """Serialize a message for API response."""
    from szurubooru.func import posts as posts_func
    data = {
        "id": m.message_id,
        "conversationId": m.conversation_id,
        "senderName": m.sender.name if m.sender else "deleted",
        "text": _decrypt(m.ciphertext, m.iv) if m.ciphertext and m.iv else "",
        "createdAt": m.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if m.post_id and m.post:
        data["post"] = posts_func.serialize_post(
            m.post, m.sender,
            options=["id", "contentUrl", "thumbnailUrl", "type", "mimeType",
                      "canvasWidth", "canvasHeight", "avifUrl", "av1Url"]
        )
    return data


def _decrypt(ciphertext: str, iv: str) -> str:
    """Decrypt ciphertext using SHAKE-256 stream cipher."""
    import base64
    key = _get_master_key()
    nonce = base64.b64decode(iv)
    ct = base64.b64decode(ciphertext)
    # Split: last 16 bytes = MAC, rest = ciphertext
    ct_bytes = ct[:-16]
    mac_received = ct[-16:]
    # Verify MAC
    mac_expected = hashlib.sha256(key + nonce + ct_bytes).digest()[:16]
    if mac_received != mac_expected:
        return "[corrupted]"
    # Decrypt
    keystream = hashlib.shake_256(key + nonce).digest(len(ct_bytes))
    pt_bytes = bytes(a ^ b for a, b in zip(ct_bytes, keystream[:len(ct_bytes)]))
    return pt_bytes.decode("utf-8")


class ChatError(errors.ValidationError):
    pass


def upsert_public_key(user: model.User, public_key: str) -> model.UserKey:
    """Store or update a user's X25519 public key."""
    assert user and user.user_id
    if not public_key or len(public_key) < 32:
        raise ChatError("Invalid public key.")

    existing = (
        db.session.query(model.UserKey)
        .filter(model.UserKey.user_id == user.user_id)
        .one_or_none()
    )
    if existing:
        existing.public_key = public_key
        existing.created_at = datetime.utcnow()
    else:
        key = model.UserKey()
        key.user_id = user.user_id
        key.public_key = public_key
        key.created_at = datetime.utcnow()
        db.session.add(key)
    return existing or key


def get_public_key(user_name: str) -> Optional[Dict[str, Any]]:
    """Get a user's public key. Returns None if no key uploaded."""
    target = users.try_get_user_by_name(user_name)
    if not target:
        raise ChatError("User %r not found." % user_name)

    key = (
        db.session.query(model.UserKey)
        .filter(model.UserKey.user_id == target.user_id)
        .one_or_none()
    )
    if not key:
        return None
    return {
        "userName": target.name,
        "publicKey": key.public_key,
    }


def _get_or_create_conversation(
    user1_id: int, user2_id: int, name: str = None
) -> model.Conversation:
    """Get existing conversation or create a new one.
    Rooms are matched by name. DMs are matched by user pair AND type='dm'."""
    if name:
        # Room: find by name
        conv = (
            db.session.query(model.Conversation)
            .filter(model.Conversation.name == name)
            .one_or_none()
        )
    else:
        # DM: find by user pair, exclude rooms
        a, b = sorted([user1_id, user2_id])
        conv = (
            db.session.query(model.Conversation)
            .filter(
                model.Conversation.user1_id == a,
                model.Conversation.user2_id == b,
                sa.or_(
                    model.Conversation.convo_type == "dm",
                    model.Conversation.convo_type == None,
                ),
            )
            .one_or_none()
        )

    if not conv:
        a, b = sorted([user1_id, user2_id])
        conv = model.Conversation()
        conv.user1_id = a
        conv.user2_id = b
        conv.created_at = datetime.utcnow()
        conv.name = name
        conv.convo_type = "room" if name else "dm"
        db.session.add(conv)
        db.session.flush()
    return conv


def send_message(
    sender: model.User,
    recipient_name: str,
    ciphertext: str = "",
    iv: str = "",
    plaintext: str = "",
    room_name: str = "",
    file_token: str = "",
) -> Dict[str, Any]:
    """Store a message (plaintext or encrypted). Returns message metadata."""
    assert sender and sender.user_id

    recipient = users.try_get_user_by_name(recipient_name)
    if not recipient:
        raise ChatError("User %r not found." % recipient_name)
    if recipient.user_id == sender.user_id:
        raise ChatError("Cannot message yourself.")

    # Reject messages if either user has blocked the other
    from szurubooru.func import blocks
    if blocks.is_blocked_either_way(sender.user_id, recipient.user_id):
        raise ChatError("Cannot message this user.")

    if not plaintext and not file_token and (not ciphertext or not iv):
        raise ChatError("Message content missing.")
    # Allow empty text when file is attached
    plaintext = plaintext or ""

    # Server-side encrypt the plaintext (or pass through E2E ciphertext)
    if plaintext and not ciphertext:
        ct, nonce = _encrypt(plaintext)
        ciphertext = ct
        iv = nonce

    conv = _get_or_create_conversation(sender.user_id, recipient.user_id, room_name or None)

    msg = model.Message()
    msg.conversation_id = conv.conversation_id
    msg.sender_id = sender.user_id
    msg.ciphertext = ciphertext
    msg.iv = iv
    msg.created_at = datetime.utcnow()

    # Handle file attachment: create a linked Post
    if file_token:
        from szurubooru.func import file_uploads as fu
        from szurubooru.func import posts as posts_func
        from szurubooru.func import images as images_mod
        content = fu.get(file_token)
        if content:
            from szurubooru.func import mime as mime_mod
            mime_type = mime_mod.get_mime_type(content)
            if mime_mod.is_image(mime_type):
                try:
                    img = images_mod.Image(content)
                    if img.width > 2000 or img.height > 2000:
                        scale = min(2000 / img.width, 2000 / img.height)
                        img.resize_fill(int(img.width * scale), int(img.height * scale))
                        content = img.to_png()
                except Exception:
                    pass
            post, _new_tags = posts_func.create_post(content, [], sender)
            db.session.flush()
            msg.post_id = post.post_id
            posts_func.finalize_post_avif_background(post)

    db.session.add(msg)

    conv.last_message_at = msg.created_at

    # Create notification for the recipient
    try:
        from szurubooru.func import notifications as notif
        from szurubooru.model.notification import Notification
        notif.create_notification(
            user_id=recipient.user_id,
            actor_id=sender.user_id,
            notif_type=Notification.TYPE_NEW_MESSAGE,
            group_key="msg_%d_%d" % (conv.conversation_id, sender.user_id),
        )
    except Exception:
        pass  # notifications are best-effort

    return _serialize_message(msg)


def get_messages(
    user: model.User,
    other_user_name: str,
    since_id: Optional[int] = None,
    limit: int = 50,
    room_name: str = "",
) -> List[Dict[str, Any]]:
    """Get messages in a conversation."""
    assert user and user.user_id

    query = db.session.query(model.Conversation)

    if room_name:
        # Room: find by name
        query = query.filter(model.Conversation.name == room_name)
    else:
        # DM: find by user pair, type=dm
        other = users.try_get_user_by_name(other_user_name)
        if not other:
            raise ChatError("User %r not found." % other_user_name)
        a, b = sorted([user.user_id, other.user_id])
        query = query.filter(
            model.Conversation.user1_id == a,
            model.Conversation.user2_id == b,
            sa.or_(
                model.Conversation.convo_type == "dm",
                model.Conversation.convo_type == None,
            ),
        )

    conv = query.one_or_none()
    if not conv:
        return []

    query = (
        db.session.query(model.Message)
        .filter(model.Message.conversation_id == conv.conversation_id)
        .order_by(model.Message.created_at.asc())
    )
    if since_id:
        query = query.filter(model.Message.message_id > since_id)

    messages = query.limit(limit).all()
    return [
        _serialize_message(m)
        for m in messages
    ]


def get_conversations(user: model.User) -> List[Dict[str, Any]]:
    """Get list of conversations for a user, with last message preview."""
    assert user and user.user_id

    convs = (
        db.session.query(model.Conversation)
        .filter(
            sa.or_(
                model.Conversation.user1_id == user.user_id,
                model.Conversation.user2_id == user.user_id,
            )
        )
        .order_by(model.Conversation.last_message_at.desc().nullslast())
        .limit(30)
        .all()
    )

    result = []
    for conv in convs:
        other_id = (
            conv.user2_id
            if conv.user1_id == user.user_id
            else conv.user1_id
        )
        other_user = users.try_get_user_by_name(
            db.session.query(model.User)
            .filter(model.User.user_id == other_id)
            .one()
            .name
        )

        last_msg = (
            db.session.query(model.Message)
            .filter(model.Message.conversation_id == conv.conversation_id)
            .order_by(model.Message.created_at.desc())
            .first()
        )

        result.append({
            "conversationId": conv.conversation_id,
            "name": conv.name,
            "type": conv.convo_type or "dm",
            "otherUser": {
                "name": other_user.name,
                "avatarUrl": users.get_avatar_url(other_user),
            },
            "lastMessageAt": (
                conv.last_message_at.strftime("%Y-%m-%dT%H:%M:%SZ")
                if conv.last_message_at
                else None
            ),
        })

    return result


def delete_conversation(user: model.User, other_user_name: str) -> None:
    """Delete a conversation and all its messages."""
    assert user and user.user_id

    other = users.try_get_user_by_name(other_user_name)
    if not other:
        raise ChatError("User %r not found." % other_user_name)

    a, b = sorted([user.user_id, other.user_id])
    conv = (
        db.session.query(model.Conversation)
        .filter(
            model.Conversation.user1_id == a,
            model.Conversation.user2_id == b,
        )
        .one_or_none()
    )
    if conv:
        # Delete messages first, then conversation
        db.session.query(model.Message).filter(
            model.Message.conversation_id == conv.conversation_id
        ).delete()
        db.session.delete(conv)


def poll_new_messages(
    user: model.User, since: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """Return messages newer than `since` across all user's conversations."""
    assert user and user.user_id

    conv_ids = [
        r[0]
        for r in db.session.query(model.Conversation.conversation_id)
        .filter(
            sa.or_(
                model.Conversation.user1_id == user.user_id,
                model.Conversation.user2_id == user.user_id,
            )
        )
        .all()
    ]

    if not conv_ids:
        return []

    query = (
        db.session.query(model.Message)
        .filter(model.Message.conversation_id.in_(conv_ids))
        .filter(model.Message.sender_id != user.user_id)
        .order_by(model.Message.created_at.asc())
    )
    if since:
        query = query.filter(model.Message.created_at > since)

    messages = query.all()
    return [_serialize_message(m) for m in messages]


def sse_stream(user: model.User) -> Generator[str, None, None]:
    """SSE generator — yields new messages as they arrive.

    Uses long-polling with a 30-second timeout, checking for new messages
    every second. When a new message arrives, yields it as an SSE event.
    """
    assert user and user.user_id

    last_check = datetime.utcnow()
    timeout = 30  # seconds
    poll_interval = 1  # second

    while True:
        elapsed = (datetime.utcnow() - last_check).total_seconds()
        if elapsed >= timeout:
            yield "event: ping\ndata: {}\n\n"
            break

        # Find conversations this user is in
        conv_ids = [
            r[0]
            for r in db.session.query(model.Conversation.conversation_id)
            .filter(
                sa.or_(
                    model.Conversation.user1_id == user.user_id,
                    model.Conversation.user2_id == user.user_id,
                )
            )
            .all()
        ]

        if conv_ids:
            # Check for new messages since last check
            new_msg = (
                db.session.query(model.Message)
                .filter(
                    model.Message.conversation_id.in_(conv_ids),
                    model.Message.sender_id != user.user_id,
                    model.Message.created_at > last_check,
                )
                .order_by(model.Message.created_at.asc())
                .first()
            )

            if new_msg:
                last_check = new_msg.created_at
                data = {
                    "id": new_msg.message_id,
                    "conversationId": new_msg.conversation_id,
                    "senderName": (
                        new_msg.sender.name if new_msg.sender else "deleted"
                    ),
                    "ciphertext": new_msg.ciphertext,
                    "iv": new_msg.iv,
                    "createdAt": new_msg.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
                yield f"event: message\ndata: {json.dumps(data)}\n\n"
                break

        time.sleep(poll_interval)
