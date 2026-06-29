import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict

from szurubooru import config, errors, rest
from szurubooru.func import mailer, users, versions

MAIL_SUBJECT = "Password reset for {name}"
MAIL_BODY = (
    "You (or someone else) requested to reset your password on {name}.\n"
    "If you wish to proceed, enter the following token in the password "
    "reset form: {token}\n"
    "This token will expire in {minutes} minutes.\n"
    "If you did not request this, please ignore this email."
)


def _hash_token(token: str) -> str:
    """Return a SHA-256 hash of the token for safe storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _generate_reset_token(user: users.model.User) -> str:
    """Generate a random token, store its hash + expiration on the user."""
    raw_token = secrets.token_urlsafe(32)
    user.password_reset_token = _hash_token(raw_token)
    user.password_reset_token_expiration = (
        datetime.utcnow() + timedelta(hours=1)
    )
    return raw_token


def _clear_reset_token(user: users.model.User) -> None:
    """Invalidate the reset token after use."""
    user.password_reset_token = None
    user.password_reset_token_expiration = None


@rest.routes.get("/password-reset/(?P<user_name>[^/]+)/?")
def start_password_reset(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    user_name = params["user_name"]
    user = users.get_user_by_name_or_email(user_name)
    if not user.email:
        raise errors.ValidationError(
            "User %r hasn't supplied email. Cannot reset password."
            % (user_name)
        )
    raw_token = _generate_reset_token(user)
    ctx.session.commit()

    mailer.send_mail(
        config.config["smtp"]["from"],
        user.email,
        MAIL_SUBJECT.format(name=config.config["name"]),
        MAIL_BODY.format(
            name=config.config["name"],
            token=raw_token,
            minutes=60,
        ),
    )

    return {}


@rest.routes.post("/password-reset/(?P<user_name>[^/]+)/?")
def finish_password_reset(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    user_name = params["user_name"]
    user = users.get_user_by_name_or_email(user_name)

    if not user.password_reset_token or not user.password_reset_token_expiration:
        raise errors.ValidationError(
            "No password reset was requested for this user."
        )

    if datetime.utcnow() > user.password_reset_token_expiration:
        _clear_reset_token(user)
        ctx.session.commit()
        raise errors.ValidationError(
            "Password reset token has expired. Please request a new one."
        )

    token = ctx.get_param_as_string("token")
    if _hash_token(token) != user.password_reset_token:
        raise errors.ValidationError("Invalid password reset token.")

    new_password = ctx.get_param_as_string("password")
    users.update_user_password(user, new_password)
    _clear_reset_token(user)
    versions.bump_version(user)
    ctx.session.commit()
    return {}
