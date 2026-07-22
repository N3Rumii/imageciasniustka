"""Mastodon API authentication middleware.

Registers a pre-hook that handles Authorization: Bearer <token>
where <token> is an existing ciasniutka UserToken value.

This hook runs BEFORE the built-in authenticator so that Bearer tokens
are resolved before the Basic/Token handler sees the header.
"""

from szurubooru import db, errors, model, rest


def _get_user_token(token_value: str):
    """Look up a UserToken by its token string alone (no username needed)."""
    return (
        db.session.query(model.UserToken)
        .filter(model.UserToken.token == token_value)
        .one_or_none()
    )


def process_bearer_auth(ctx: rest.Context) -> None:
    """Pre-hook: handle Authorization: Bearer <token>."""
    if not ctx.has_header("Authorization"):
        return

    header = ctx.get_header("Authorization")
    parts = header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return

    token_value = parts[1]

    user_token = _get_user_token(token_value)
    if user_token is None:
        raise errors.AuthError("Invalid access token.")

    from szurubooru.func import auth as auth_func

    if not auth_func.is_valid_token(user_token):
        raise errors.AuthError("Token expired or disabled.")

    # Public client-credentials tokens have no user; keep the
    # default anonymous user set by the framework.
    if user_token.user is not None:
        ctx.user = user_token.user

    # Remove the Authorization header so the built-in authenticator
    # (which runs after us) doesn't reject "Bearer" as an unknown type.
    ctx._headers.pop("Authorization", None)


def register():
    """Install the Bearer auth hook at the front of the pre-hook chain
    so it runs before the built-in Basic/Token authenticator."""
    rest.middleware.pre_hooks.insert(0, process_bearer_auth)
