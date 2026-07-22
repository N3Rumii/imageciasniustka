"""Chat API — encrypted messaging endpoints.

All crypto happens client-side. The server is a dumb relay.
"""

import json
from typing import Dict

from szurubooru import db, rest
from szurubooru.func import auth, chat


def _json_response(data: dict, status: int = 200) -> rest.Response:
    """Return a JSON response dict (the framework serializes it)."""
    return data


@rest.routes.post("/chat/keys/?")
def upload_key(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    """Upload or update the user's X25519 public key."""
    auth.verify_privilege(ctx.user, "users:view")
    public_key = ctx.get_param_as_string("publicKey")
    chat.upsert_public_key(ctx.user, public_key)
    ctx.session.commit()
    return {"ok": True}


@rest.routes.get("/chat/keys/(?P<user_name>[^/]+)/?")
def get_key(ctx: rest.Context, params: Dict[str, str]) -> rest.Response:
    """Get a user's public key for initiating E2E conversation."""
    auth.verify_privilege(ctx.user, "users:view")
    key = chat.get_public_key(params["user_name"])
    if not key:
        return {"publicKey": None, "userName": params["user_name"]}
    return key


@rest.routes.post("/chat/messages/?")
def send_message(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    """Send an encrypted message. Body: {recipient, ciphertext, iv}."""
    auth.verify_privilege(ctx.user, "users:view")
    recipient = ctx.get_param_as_string("recipient")
    ciphertext = ctx.get_param_as_string("ciphertext", default="")
    iv = ctx.get_param_as_string("iv", default="")
    plaintext = ctx.get_param_as_string("text", default="")
    room_name = ctx.get_param_as_string("roomName", default="")
    file_tokens = ctx.get_param_as_list("fileTokens", default=[])
    file_token = file_tokens[0] if file_tokens else ctx.get_param_as_string("fileToken", default="")
    # TODO: support multiple file tokens in one message
    msg = chat.send_message(ctx.user, recipient, ciphertext, iv, plaintext, room_name, file_token)
    ctx.session.commit()
    return msg


@rest.routes.get("/chat/messages/(?P<user_name>[^/]+)/?")
def get_messages(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    """Get messages with a specific user."""
    auth.verify_privilege(ctx.user, "users:view")
    since_id = ctx.get_param_as_int("since", default=None)
    room_name = ctx.get_param_as_string("room", default="")
    messages = chat.get_messages(ctx.user, params["user_name"], since_id, room_name=room_name)
    return {"results": messages}


@rest.routes.post("/chat/upload/?")
def chat_upload(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    """Upload a file for chat attachment. Returns a token for send_message."""
    auth.verify_privilege(ctx.user, "users:view")
    content = ctx.get_file("content")
    if not content:
        raise rest.errors.HttpBadRequest("ValidationError", "File content missing.")
    from szurubooru.func import file_uploads
    token = file_uploads.save(content)
    return {"token": token}


@rest.routes.get("/chat/conversations/?")
def get_conversations(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    """Get list of conversations."""
    auth.verify_privilege(ctx.user, "users:view")
    convs = chat.get_conversations(ctx.user)
    return {"results": convs}


@rest.routes.delete("/chat/conversations/(?P<user_name>[^/]+)/?")
def delete_conversation(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    """Delete a conversation and all its messages."""
    auth.verify_privilege(ctx.user, "users:view")
    chat.delete_conversation(ctx.user, params["user_name"])
    ctx.session.commit()
    return {"ok": True}


@rest.routes.get("/chat/poll/?")
def poll_messages(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    """Poll for new messages across all conversations since last check."""
    auth.verify_privilege(ctx.user, "users:view")
    since = ctx.get_param_as_string("since", default="")
    import datetime as dt_mod
    since_dt = None
    if since:
        try:
            since_dt = dt_mod.datetime.fromisoformat(since)
        except (ValueError, TypeError):
            pass
    result = chat.poll_new_messages(ctx.user, since_dt)
    return {"results": result, "serverTime": dt_mod.datetime.utcnow().isoformat()}
