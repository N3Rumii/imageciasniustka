"""
Add content_token to posts for non-deterministic file URLs

Revision ID: c1a2b3c4d5e6
Created at: 2026-06-30
"""

import os
import re
import secrets

import sqlalchemy as sa
from alembic import op

from szurubooru.func.posts import get_post_security_hash

revision = "c1a2b3c4d5e6"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


class _PostProxy:
    """Minimal Post-like object for hash computation during migration."""
    def __init__(self, post_id: int, token: str):
        self.post_id = post_id
        self.content_token = token


def upgrade():
    # Step 1: Add the column
    op.add_column(
        "post",
        sa.Column("content_token", sa.Unicode(32), nullable=True),
    )

    # Step 2: Generate and assign a random token to every existing post
    connection = op.get_bind()
    posts = sa.table(
        "post",
        sa.column("id", sa.Integer),
        sa.column("content_token", sa.Unicode(32)),
    )

    rows = connection.execute(sa.select(posts.c.id)).fetchall()
    tokens = {}
    for (post_id,) in rows:
        token = secrets.token_hex(16)
        tokens[post_id] = token
        connection.execute(
            sa.update(posts)
            .where(posts.c.id == post_id)
            .values(content_token=token)
        )

    # Step 3: Rename existing files to use the new token-based hash
    data_dir = "/data/data/com.termux/files/home/hosting_cias/data"
    for directory in [
        "posts",
        "posts/custom-thumbnails",
        "generated-thumbnails",
        "generated-avif",
        "generated-av1",
    ]:
        dir_path = os.path.join(data_dir, directory)
        if not os.path.isdir(dir_path):
            continue
        for entry in os.scandir(dir_path):
            match = re.match(
                r"^(?P<pid>\d+)_(?P<old_hash>[0-9a-f]+)\.(?P<ext>\w+)$",
                entry.name,
            )
            if not match:
                continue
            post_id = int(match.group("pid"))
            ext = match.group("ext")
            if post_id not in tokens:
                continue
            proxy = _PostProxy(post_id, tokens[post_id])
            new_hash = get_post_security_hash(proxy)
            new_name = "%d_%s.%s" % (post_id, new_hash, ext)
            if entry.name == new_name:
                continue
            old_path = os.path.join(dir_path, entry.name)
            new_path = os.path.join(dir_path, new_name)
            os.rename(old_path, new_path)


def downgrade():
    op.drop_column("post", "content_token")
