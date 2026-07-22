"""Mastodon /api/v2/media endpoint for image uploads.

Files uploaded here are stored temporarily in an in-memory dict
keyed by an auto-generated attachment ID.  When a status is created
with media_ids[], the stored bytes are retrieved and used as the
status image.
"""

import uuid
from typing import Dict

from szurubooru import errors, rest

# In-memory store: attachment_id → bytes
# In production this would be backed by a database table or a temp
# file store, but the existing szurubooru architecture handles file
# storage through the uploads table.  This simple dict is adequate
# for the ephemeral upload → status-create flow.
_upload_store: Dict[str, bytes] = {}


def pop_upload(attachment_id: str):
    """Retrieve and remove an upload from the temporary store."""
    return _upload_store.pop(attachment_id, None)


@rest.routes.post("/api/v2/media/?")
def upload_media(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    """Accept a media file upload, return a Mastodon MediaAttachment."""
    if not ctx.has_file("file"):
        raise errors.ValidationError("No file attached.")

    file_content = ctx.get_file("file")
    attachment_id = uuid.uuid4().hex
    _upload_store[attachment_id] = file_content

    return {
        "id": attachment_id,
        "type": "image",  # Mastodon apps use this to decide rendering
        "url": "",
        "preview_url": "",
        "remote_url": None,
        "preview_remote_url": None,
        "text_url": None,
        "meta": {"original": {}},
        "description": None,
        "blurhash": None,
    }
