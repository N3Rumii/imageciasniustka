"""Mastodon OAuth2 endpoints — app registration and token grant.

POST /api/v1/apps  — register a client application
POST /oauth/token   — obtain an access token (password grant)
"""

import uuid
from datetime import datetime
from typing import Dict

from szurubooru import config, db, errors, model, rest
from szurubooru.func import auth, user_tokens, users


# ---------------------------------------------------------------------------
# POST /api/v1/apps
# ---------------------------------------------------------------------------

@rest.routes.post("/api/v1/apps/?")
def create_app(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    client_name = ctx.get_param_as_string("client_name")
    redirect_uris = ctx.get_param_as_string("redirect_uris", default="urn:ietf:wg:oauth:2.0:oob")
    scopes = ctx.get_param_as_string("scopes", default="read write follow")
    website = ctx.get_param_as_string("website", default=None)

    if not client_name:
        raise errors.ValidationError("client_name is required.")

    oauth_client = model.OAuth2Client()
    oauth_client.client_id = uuid.uuid4().hex
    oauth_client.client_secret = uuid.uuid4().hex
    oauth_client.client_name = client_name
    oauth_client.redirect_uris = redirect_uris
    oauth_client.website = website or None
    oauth_client.scopes = scopes
    oauth_client.creation_time = datetime.utcnow()
    # If the user is already authenticated, link the app to them
    if ctx.user and ctx.user.user_id:
        oauth_client.user_id = ctx.user.user_id

    ctx.session.add(oauth_client)
    ctx.session.commit()

    return {
        "id": str(oauth_client.oauth2_client_id),
        "name": oauth_client.client_name,
        "website": oauth_client.website,
        "redirect_uri": oauth_client.redirect_uris,
        "client_id": oauth_client.client_id,
        "client_secret": oauth_client.client_secret,
        "vapid_key": None,
    }


# ---------------------------------------------------------------------------
# POST /oauth/token
# ---------------------------------------------------------------------------

@rest.routes.post("/oauth/token/?")
def oauth_token(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    grant_type = ctx.get_param_as_string("grant_type")

    if grant_type == "password":
        return _password_grant(ctx)
    elif grant_type == "client_credentials":
        return _client_credentials_grant(ctx)
    else:
        raise errors.ValidationError(
            "Unsupported grant_type: %s. Supported: password, client_credentials."
            % grant_type
        )


def _password_grant(ctx: rest.Context) -> rest.Response:
    username = ctx.get_param_as_string("username")
    password = ctx.get_param_as_string("password")
    scopes = ctx.get_param_as_string("scope", default="read write follow")

    try:
        user = users.get_user_by_name(username)
    except users.UserNotFoundError:
        raise errors.AuthError("Invalid username or password.")

    if not auth.is_valid_password(user, password):
        raise errors.AuthError("Invalid username or password.")

    # Look for an existing mastodon-tagged UserToken for this user
    existing_token = (
        db.session.query(model.UserToken)
        .filter(
            model.UserToken.user_id == user.user_id,
            model.UserToken.note == "mastodon-oauth2",
            model.UserToken.enabled == True,  # noqa: E712
        )
        .order_by(model.UserToken.creation_time.desc())
        .first()
    )

    if existing_token:
        access_token_str = existing_token.token
        # Bump usage time
        existing_token.last_usage_time = datetime.utcnow()
        ctx.session.commit()
    else:
        # Create a new UserToken for this user
        user_token = model.UserToken()
        user_token.user = user
        user_token.token = uuid.uuid4().hex
        user_token.note = "mastodon-oauth2"
        user_token.enabled = True
        user_token.creation_time = datetime.utcnow()
        user_token.last_usage_time = datetime.utcnow()
        ctx.session.add(user_token)
        ctx.session.flush()
        access_token_str = user_token.token
        ctx.session.commit()

    return {
        "access_token": access_token_str,
        "token_type": "Bearer",
        "scope": scopes,
        "created_at": int(datetime.utcnow().timestamp()),
    }


def _client_credentials_grant(ctx: rest.Context) -> rest.Response:
    """Client credentials grant — returns a token associated with
    the anonymous user for public API access."""
    client_id = ctx.get_param_as_string("client_id")
    client_secret = ctx.get_param_as_string("client_secret")
    scopes = ctx.get_param_as_string("scope", default="read")

    # Validate client credentials
    if client_id and client_secret:
        oauth_client = (
            db.session.query(model.OAuth2Client)
            .filter(model.OAuth2Client.client_id == client_id)
            .one_or_none()
        )
        if not oauth_client or oauth_client.client_secret != client_secret:
            raise errors.AuthError("Invalid client credentials.")

    # For client_credentials, return a special public-access token.
    # We create a token linked to no user (user_id=NULL) — this will
    # resolve to anonymous in the middleware.
    public_token = model.UserToken()
    public_token.user_id = None  # anonymous
    public_token.token = "public-" + uuid.uuid4().hex[:16]
    public_token.note = "mastodon-client-credentials"
    public_token.enabled = True
    public_token.creation_time = datetime.utcnow()
    public_token.last_usage_time = datetime.utcnow()
    ctx.session.add(public_token)
    ctx.session.flush()
    access_token_str = public_token.token
    ctx.session.commit()

    return {
        "access_token": access_token_str,
        "token_type": "Bearer",
        "scope": scopes,
        "created_at": int(datetime.utcnow().timestamp()),
    }
