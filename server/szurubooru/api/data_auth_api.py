import json
import re
from typing import Dict
from urllib.parse import unquote

from szurubooru import rest
from szurubooru.func import auth, posts, user_tokens, users

# Content filenames have the pattern: {post_id}_{security_hash}.{ext}
# e.g., /data/generated-avif/19_bc6f411bcc0e9783.avif
#       /data/generated-thumbnails/19_bc6f411bcc0e9783.avif
#       /data/posts/19_bc6f411bcc0e9783.jpg
#       /data/posts/custom-thumbnails/19_bc6f411bcc0e9783.png
#       /data/generated-av1/19_bc6f411bcc0e9783.webm
_POST_ID_PATTERN = re.compile(r"/(\d+)_[0-9a-f]{16}\.\w+$")


def _extract_post_id(path: str) -> int:
    """Extract post ID from a content file path. Returns None if not a post."""
    match = _POST_ID_PATTERN.search(path)
    return int(match.group(1)) if match else None


def _try_auth_via_cookie(ctx: rest.Context) -> None:
    """
    Try to authenticate via the 'auth' cookie that the client stores after
    login. Browsers send cookies with <img> requests but not Authorization
    headers, so we need this as a fallback for content file access.
    """
    cookie_header = ctx.get_header("Cookie")
    if not cookie_header:
        return

    # Parse the 'auth' cookie from the Cookie header
    # Cookie format: "auth=%7B%22user%22%3A%22...%22%7D; other=..."
    for part in cookie_header.split(";"):
        part = part.strip()
        if part.startswith("auth="):
            try:
                value = unquote(part[5:])
                data = json.loads(value)
                username = data.get("user")
                token = data.get("token")
                if not username or not token:
                    return

                user = users.get_user_by_name(username)
                user_token = user_tokens.get_by_user_and_token(user, token)
                if user_token and auth.is_valid_token(user_token):
                    ctx.user = user
            except Exception:
                pass
            break


@rest.routes.get("/data-auth/.*")
def check_data_access(
    ctx: rest.Context, _params: Dict[str, str]
) -> rest.Response:
    """
    Called by nginx auth_request before serving /data/ files.
    The URL includes the original data path, e.g.:
        /data-auth/data/generated-avif/19_hash.avif

    Returns empty 200 if access allowed, raises 403 if denied.
    Non-post files (avatars, etc.) are always allowed.

    Authenticates via Authorization header (API requests) or auth cookie
    (browser image/resource requests).
    """
    path = ctx.url
    post_id = _extract_post_id(path)

    if post_id is None:
        # Not a post file — allow (avatars, etc.)
        return {}

    # If the authorization middleware didn't find a user (no Authorization
    # header on <img> requests), try authenticating via the auth cookie.
    if ctx.user.user_id is None:
        _try_auth_via_cookie(ctx)

    post = posts.try_get_post_by_id(post_id, ctx.user)
    if post is None:
        raise rest.errors.HttpForbidden(
            "AccessDenied",
            "You do not have permission to access this content.",
        )

    return {}
