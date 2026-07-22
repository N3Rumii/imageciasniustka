"""Mastodon REST API compatibility layer.

Import this module during app startup to register all Mastodon API
routes and authentication hooks on top of ciasniutka's existing
business logic.

Existing users can connect Mastodon apps directly by using their
ciasniutka UserToken as a Bearer token — no migration needed.
"""

from szurubooru.mastodon.middleware import register as _register_middleware

_register_middleware()

# Import endpoint modules to register routes
import szurubooru.mastodon.instance       # noqa: E402,F401
import szurubooru.mastodon.accounts       # noqa: E402,F401
import szurubooru.mastodon.oauth          # noqa: E402,F401
import szurubooru.mastodon.statuses       # noqa: E402,F401
import szurubooru.mastodon.timelines      # noqa: E402,F401
import szurubooru.mastodon.media          # noqa: E402,F401
import szurubooru.mastodon.notifications  # noqa: E402,F401
import szurubooru.mastodon.search         # noqa: E402,F401
