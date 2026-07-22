"""Mastodon /api/v1/instance and /api/v2/instance endpoints."""

from typing import Dict

from szurubooru import rest
from szurubooru.mastodon.serializers import (
    serialize_instance_v1,
    serialize_instance_v2,
)


@rest.routes.get("/api/v1/instance/?")
def instance_v1(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    return serialize_instance_v1()


@rest.routes.get("/api/v2/instance/?")
def instance_v2(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    return serialize_instance_v2()
