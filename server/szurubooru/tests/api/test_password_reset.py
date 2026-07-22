import hashlib
import secrets
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from szurubooru import api, db, errors, model
from szurubooru.func import auth, mailer


@pytest.fixture(autouse=True)
def inject_config(config_injector):
    config_injector(
        {
            "secret": "x",
            "domain": "http://example.com",
            "name": "Test instance",
            "smtp": {
                "from": "noreply@example.com",
            },
        }
    )


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def test_reset_sending_email(context_factory, user_factory):
    db.session.add(
        user_factory(
            name="u1", rank=model.User.RANK_REGULAR, email="user@example.com"
        )
    )
    db.session.flush()
    for initiating_user in ["u1", "user@example.com"]:
        with patch("szurubooru.func.mailer.send_mail"):
            assert (
                api.password_reset_api.start_password_reset(
                    context_factory(), {"user_name": initiating_user}
                )
                == {}
            )
            mailer.send_mail.assert_called_once()
            # Verify the email contains a token (not a URL-based token)
            call_args = mailer.send_mail.call_args[0]
            assert "token" in call_args[1]  # recipient
            assert "Test instance" in call_args[1]  # subject
            assert "token" in call_args[1].lower()  # body mentions token


def test_trying_to_reset_non_existing(context_factory):
    with pytest.raises(errors.NotFoundError):
        api.password_reset_api.start_password_reset(
            context_factory(), {"user_name": "u1"}
        )


def test_trying_to_reset_without_email(context_factory, user_factory):
    db.session.add(
        user_factory(name="u1", rank=model.User.RANK_REGULAR, email=None)
    )
    db.session.flush()
    with pytest.raises(errors.ValidationError):
        api.password_reset_api.start_password_reset(
            context_factory(), {"user_name": "u1"}
        )


def test_confirming_with_good_token(context_factory, user_factory):
    user = user_factory(
        name="u1", rank=model.User.RANK_REGULAR, email="user@example.com"
    )
    old_hash = user.password_hash
    db.session.add(user)
    db.session.flush()

    # Simulate a password reset request to create a token
    raw_token = None

    # Patch secrets.token_urlsafe to get a known token
    with patch("secrets.token_urlsafe") as mock_urlsafe:
        mock_urlsafe.return_value = "test-token-value"
        api.password_reset_api.start_password_reset(
            context_factory(), {"user_name": "u1"}
        )
        raw_token = "test-token-value"

    # Now confirm with the token and a new password
    context = context_factory(
        params={"token": raw_token, "password": "newpassword"}
    )
    result = api.password_reset_api.finish_password_reset(
        context, {"user_name": "u1"}
    )
    assert result == {}
    assert user.password_hash != old_hash
    assert auth.is_valid_password(user, "newpassword") is True
    # Token should be cleared after use
    assert user.password_reset_token is None
    assert user.password_reset_token_expiration is None


def test_confirming_with_expired_token(context_factory, user_factory):
    user = user_factory(
        name="u1", rank=model.User.RANK_REGULAR, email="user@example.com"
    )
    db.session.add(user)
    db.session.flush()

    # Manually set an expired token on the user
    user.password_reset_token = _hash_token("expired-token")
    user.password_reset_token_expiration = (
        datetime.utcnow() - timedelta(hours=1)
    )
    db.session.flush()

    context = context_factory(
        params={"token": "expired-token", "password": "newpassword"}
    )
    with pytest.raises(errors.ValidationError):
        api.password_reset_api.finish_password_reset(
            context, {"user_name": "u1"}
        )


def test_trying_to_confirm_non_existing(context_factory):
    with pytest.raises(errors.NotFoundError):
        api.password_reset_api.finish_password_reset(
            context_factory(), {"user_name": "u1"}
        )


def test_trying_to_confirm_without_token(context_factory, user_factory):
    db.session.add(
        user_factory(
            name="u1", rank=model.User.RANK_REGULAR, email="user@example.com"
        )
    )
    db.session.flush()
    with pytest.raises(errors.ValidationError):
        api.password_reset_api.finish_password_reset(
            context_factory(params={}), {"user_name": "u1"}
        )


def test_trying_to_confirm_with_bad_token(context_factory, user_factory):
    db.session.add(
        user_factory(
            name="u1", rank=model.User.RANK_REGULAR, email="user@example.com"
        )
    )
    db.session.flush()
    with pytest.raises(errors.ValidationError):
        api.password_reset_api.finish_password_reset(
            context_factory(
                params={"token": "bad", "password": "newpassword"}
            ),
            {"user_name": "u1"},
        )


def test_trying_to_confirm_without_password(context_factory, user_factory):
    user = user_factory(
        name="u1", rank=model.User.RANK_REGULAR, email="user@example.com"
    )
    db.session.add(user)
    db.session.flush()

    # Set up a valid token
    raw_token = "valid-token"
    user.password_reset_token = _hash_token(raw_token)
    user.password_reset_token_expiration = (
        datetime.utcnow() + timedelta(hours=1)
    )
    db.session.flush()

    context = context_factory(params={"token": raw_token})
    with pytest.raises(errors.MissingRequiredParameterError):
        api.password_reset_api.finish_password_reset(
            context, {"user_name": "u1"}
        )
