from typing import Any, Dict, List, Optional, Tuple

import sqlalchemy as sa

from szurubooru import db, errors, model
from szurubooru.search import criteria, tokens
from szurubooru.search.configs.base_search_config import BaseSearchConfig
from szurubooru.search.configs import util as search_util
from szurubooru.search.query import SearchQuery
from szurubooru.search.typing import SaColumn, SaQuery


def _create_followed_filter(user: Optional[model.User]):
    """Create a filter that matches statuses from users followed by `user`."""
    from szurubooru.model.user_follow import UserFollow

    def wrapper(query, criterion, negated):
        if not user or not user.user_id:
            return query.filter(sa.literal(False)) if not negated else query
        followed_user_ids = (
            sa.select(UserFollow.followee_id)
            .where(UserFollow.follower_id == user.user_id)
            .scalar_subquery()
        )
        expr = model.Status.user_id.in_(followed_user_ids)
        if negated:
            expr = ~expr
        return query.filter(expr)

    return wrapper


class StatusSearchConfig(BaseSearchConfig):
    """Search configuration for statuses (timeline tweets)."""

    def __init__(self) -> None:
        super().__init__()
        self.user: Optional[model.User] = None

    @property
    def root(self) -> SaQuery:
        return db.session.query(model.Status)

    @property
    def id_column(self) -> SaColumn:
        return model.Status.status_id

    @property
    def creation_time_column(self) -> SaColumn:
        return model.Status.creation_time

    @property
    def last_edit_time_column(self) -> SaColumn:
        return model.Status.last_edit_time

    @property
    def anonymous_filter(self) -> SaQuery:
        return self.root.filter(model.Status.private == False)  # noqa: E712

    @property
    def named_filters(self) -> Dict[str, Any]:
        return {
            "id": model.Status.status_id,
            "user": model.Status.user_id,
            "tag": model.StatusHashtag.tag_id,
            "text": model.Status.text,
            "has-image": model.Status.post_id,
            "followed": _create_followed_filter(self.user),
        }

    @property
    def sort_columns(self) -> Dict[str, Tuple[SaColumn, str]]:
        return {
            "creation-date": (model.Status.creation_time, self.SORT_DESC),
            "creation-time": (model.Status.creation_time, self.SORT_DESC),
            "date": (model.Status.creation_time, self.SORT_DESC),
            "time": (model.Status.creation_time, self.SORT_DESC),
            "id": (model.Status.status_id, self.SORT_DESC),
        }

    @property
    def special_filters(self) -> Dict[str, Any]:
        return {
            "feed": self.noop_filter,
        }

    def on_search_query_parsed(self, search_query: SearchQuery) -> SaQuery:
        new_special_tokens = []
        for token in search_query.special_tokens:
            if token.value == "feed":
                assert self.user
                if not self.user or self.user.rank == "anonymous":
                    raise errors.SearchError(
                        "Must be logged in to use this feature."
                    )
                criterion = criteria.PlainCriterion(
                    original_text=self.user.name, value=self.user.name
                )
                setattr(criterion, "internal", True)
                search_query.named_tokens.append(
                    tokens.NamedToken(
                        name="followed",
                        criterion=criterion,
                        negated=token.negated,
                    )
                )
            else:
                new_special_tokens.append(token)
        search_query.special_tokens = new_special_tokens

    @property
    def searchable_columns(self) -> List[SaColumn]:
        return [model.Status.text]
