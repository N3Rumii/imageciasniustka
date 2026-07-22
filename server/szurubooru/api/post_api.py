import base64
import subprocess
from datetime import datetime
from typing import Dict, List, Optional

from szurubooru import db, errors, model, rest, search
from szurubooru.func import (
    auth,
    favorites,
    files,
    mime,
    notifications,
    posts,
    scores,
    serialization,
    snapshots,
    tags,
    users,
    util,
    versions,
)

_search_executor_config = search.configs.PostSearchConfig()
_search_executor = search.Executor(_search_executor_config)


def _get_post_id(params: Dict[str, str]) -> int:
    try:
        return int(params["post_id"])
    except TypeError:
        raise posts.InvalidPostIdError(
            "Invalid post ID: %r." % params["post_id"]
        )


def _get_post(
    params: Dict[str, str], user: Optional[model.User] = None
) -> model.Post:
    return posts.get_post_by_id(_get_post_id(params), user)


def _serialize_post(
    ctx: rest.Context, post: Optional[model.Post]
) -> rest.Response:
    return posts.serialize_post(
        post, ctx.user, options=serialization.get_serialization_options(ctx)
    )


@rest.routes.get("/posts/?")
def get_posts(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    auth.verify_privilege(ctx.user, "posts:list")
    _search_executor_config.user = ctx.user
    return _search_executor.execute_and_serialize(
        ctx, lambda post: _serialize_post(ctx, post)
    )


@rest.routes.post("/posts/?")
def create_post(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    anonymous = ctx.get_param_as_bool("anonymous", default=False)
    if anonymous:
        auth.verify_privilege(ctx.user, "posts:create:anonymous")
    else:
        auth.verify_privilege(ctx.user, "posts:create:identified")
    content = ctx.get_file(
        "content",
        use_video_downloader=auth.has_privilege(
            ctx.user, "uploads:use_downloader"
        ),
    )
    tag_names = ctx.get_param_as_string_list("tags", default=[])
    safety = ctx.get_param_as_string("safety")
    source = ctx.get_param_as_string("source", default="")
    if ctx.has_param("contentUrl") and not source:
        source = ctx.get_param_as_string("contentUrl", default="")
    relations = ctx.get_param_as_int_list("relations", default=[])
    notes = ctx.get_param_as_list("notes", default=[])
    flags = ctx.get_param_as_string_list(
        "flags", default=posts.get_default_flags(content)
    )
    is_private = ctx.get_param_as_bool("private", default=False)
    whitelist_raw = ctx.get_param_as_list("whitelist", default=[])
    whitelist_user_ids = None
    if is_private:
        whitelist_user_ids = []
        for item in whitelist_raw:
            if isinstance(item, int) or (
                isinstance(item, str) and item.isdigit()
            ):
                whitelist_user_ids.append(int(item))
            elif isinstance(item, str) and item.strip():
                user = users.get_user_by_name(item.strip())
                if user:
                    whitelist_user_ids.append(user.user_id)
        # If private but no users specified, add the uploader as the
        # sole whitelist entry so the post is marked as private
        if not whitelist_user_ids and not anonymous:
            whitelist_user_ids.append(ctx.user.user_id)

    post, new_tags = posts.create_post(
        content, tag_names, None if anonymous else ctx.user,
        whitelist_user_ids=whitelist_user_ids,
    )
    if len(new_tags):
        auth.verify_privilege(ctx.user, "tags:create")

    posts.update_post_safety(post, safety)
    posts.update_post_source(post, source)
    posts.update_post_relations(post, relations)
    posts.update_post_notes(post, notes)
    posts.update_post_flags(post, flags)
    if ctx.has_file("thumbnail"):
        posts.update_post_thumbnail(post, ctx.get_file("thumbnail"))

    # Store audio metadata as source for display in player
    # (must run AFTER update_post_source so it isn't wiped)
    audio_meta = getattr(post, "_audio_metadata", None)
    if audio_meta and (audio_meta.get("title") or audio_meta.get("artist")):
        import json
        post.source = json.dumps({
            "title": audio_meta.get("title") or "",
            "artist": audio_meta.get("artist") or "",
            "album": audio_meta.get("album") or "",
        })

    ctx.session.add(post)
    ctx.session.flush()
    create_snapshots_for_post(post, new_tags, None if anonymous else ctx.user)
    ctx.session.flush()
    if not anonymous:
        notifications.notify_followers_new_post(post, ctx.user)
    ctx.session.commit()
    posts.finalize_post_avif_background(post)
    if post.type == model.Post.TYPE_AUDIO:
        posts.finalize_post_opus_background(post)
    return _serialize_post(ctx, post)


def create_snapshots_for_post(
    post: model.Post, new_tags: List[model.Tag], user: Optional[model.User]
):
    snapshots.create(post, user)
    # Flush immediately so the post snapshot INSERT isn't batched with
    # tag snapshots. SQLAlchemy's bulk INSERT ... RETURNING sends VALUES
    # in alphabetic column order, which misaligns with the DB column order
    # when different entity types (post vs tag) are mixed in one statement.
    db.session.flush()
    for tag in new_tags:
        try:
            snapshots.create(tag, user)
            db.session.flush()
        except Exception:
            pass


@rest.routes.get("/post/(?P<post_id>[^/]+)/whitelist/?")
def get_post_whitelist(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    auth.verify_privilege(ctx.user, "posts:view")
    post = _get_post(params, ctx.user)
    if post.user_id != ctx.user.user_id:
        raise auth.AuthError("Only the uploader can view the whitelist.")
    return {
        "results": [
            {"id": u.user_id, "name": u.name}
            for u in post.whitelist_users
        ]
    }


@rest.routes.post("/post/(?P<post_id>[^/]+)/whitelist/?")
def set_post_whitelist(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    auth.verify_privilege(ctx.user, "posts:edit:tags")
    post = _get_post(params, ctx.user)
    if post.user_id != ctx.user.user_id:
        raise auth.AuthError("Only the uploader can modify the whitelist.")
    raw = ctx.get_param_as_list("userIds", default=[])
    user_ids = []
    for item in raw:
        if isinstance(item, int) or (isinstance(item, str) and item.isdigit()):
            user_ids.append(int(item))
        elif isinstance(item, str) and item.strip():
            u = users.get_user_by_name(item.strip())
            if u:
                user_ids.append(u.user_id)
    posts.update_post_whitelist(post, user_ids)
    ctx.session.commit()
    return _serialize_post(ctx, post)


@rest.routes.get("/post/(?P<post_id>[^/]+)/download/?")
def download_post(ctx: rest.Context, params: Dict[str, str]) -> rest.Response:
    auth.verify_privilege(ctx.user, "posts:view")
    post = _get_post(params, ctx.user)
    target_format = ctx.get_param_as_string("format", default="png").lower()
    allowed_formats = ("png", "jpeg", "jpg", "mp4", "gif", "jxl")
    if target_format not in allowed_formats:
        raise errors.ValidationError(
            "Format must be one of: %s" % ", ".join(allowed_formats)
        )

    # Determine source: AVIF for images, AV1 for videos
    if post.type == model.Post.TYPE_VIDEO:
        source_path = posts.get_post_av1_path(post)
        source_ext = "webm"
    else:
        source_path = posts.get_post_avif_path(post)
        source_ext = "avif"
    source_data = files.get(source_path)
    if not source_data:
        raise posts.PostNotFoundError("Source file not found.")

    with util.create_temp_file(suffix="." + source_ext) as tmp_in:
        tmp_in.write(source_data)
        tmp_in.flush()

        # JXL: use cjxl encoder after extracting a PNG frame with ffmpeg
        if target_format == "jxl":
            with util.create_temp_file_path(suffix=".png") as tmp_png:
                ff_args = [
                    "ffmpeg", "-loglevel", "24",
                    "-i", tmp_in.name, "-y",
                    "-f", "image2", "-vframes", "1", tmp_png,
                ]
                subprocess.run(ff_args, check=True, capture_output=True)
                with util.create_temp_file_path(suffix=".jxl") as tmp_out:
                    cjxl_args = [
                        "cjxl", tmp_png, tmp_out,
                        "-d", "1",  # lossless
                        "-e", "4",  # medium effort
                    ]
                    subprocess.run(cjxl_args, check=True, capture_output=True)
                    with open(tmp_out, "rb") as f:
                        out_data = f.read()
        else:
            with util.create_temp_file_path(
                suffix="." + target_format
            ) as tmp_out:
                args = [
                    "ffmpeg", "-loglevel", "24",
                    "-i", tmp_in.name, "-y", tmp_out,
                ]
                if target_format == "gif":
                    args += [
                        "-vf", "split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
                        "-loop", "0",
                    ]
                elif target_format in ("png", "jpeg", "jpg"):
                    args += ["-f", "image2", "-vframes", "1"]
                else:
                    args += ["-c:v", "libx264", "-preset", "fast", "-crf", "23"]
                subprocess.run(args, check=True, capture_output=True)
                with open(tmp_out, "rb") as f:
                    out_data = f.read()
    return {
        "data": base64.b64encode(out_data).decode("ascii"),
        "mimeType": (
            "video/mp4" if target_format == "mp4"
            else "image/jxl" if target_format == "jxl"
            else "image/" + target_format
        ),
        "fileName": "post_%d.%s" % (post.post_id, target_format),
    }


@rest.routes.get("/post/(?P<post_id>[^/]+)/?")
def get_post(ctx: rest.Context, params: Dict[str, str]) -> rest.Response:
    auth.verify_privilege(ctx.user, "posts:view")
    post = _get_post(params, ctx.user)
    return _serialize_post(ctx, post)


@rest.routes.put("/post/(?P<post_id>[^/]+)/?")
def update_post(ctx: rest.Context, params: Dict[str, str]) -> rest.Response:
    post = _get_post(params, ctx.user)
    versions.verify_version(post, ctx)
    versions.bump_version(post)
    if ctx.has_file("content"):
        auth.verify_privilege(ctx.user, "posts:edit:content")
        posts.update_post_content(
            post,
            ctx.get_file(
                "content",
                use_video_downloader=auth.has_privilege(
                    ctx.user, "uploads:use_downloader"
                ),
            ),
        )
    if ctx.has_param("tags"):
        auth.verify_privilege(ctx.user, "posts:edit:tags")
        new_tags = posts.update_post_tags(
            post, ctx.get_param_as_string_list("tags")
        )
        if len(new_tags):
            auth.verify_privilege(ctx.user, "tags:create")
            db.session.flush()
            for tag in new_tags:
                try:
                    snapshots.create(tag, ctx.user)
                    db.session.flush()
                except Exception:
                    pass
    if ctx.has_param("safety"):
        auth.verify_privilege(ctx.user, "posts:edit:safety")
        posts.update_post_safety(post, ctx.get_param_as_string("safety"))
    if ctx.has_param("source"):
        auth.verify_privilege(ctx.user, "posts:edit:source")
        posts.update_post_source(post, ctx.get_param_as_string("source"))
    elif ctx.has_param("contentUrl"):
        posts.update_post_source(post, ctx.get_param_as_string("contentUrl"))
    if ctx.has_param("relations"):
        auth.verify_privilege(ctx.user, "posts:edit:relations")
        posts.update_post_relations(
            post, ctx.get_param_as_int_list("relations")
        )
    if ctx.has_param("pools"):
        auth.verify_privilege(ctx.user, "pools:edit:posts")
        pool_identifiers = ctx.get_param_as_string_list("pools")
        from szurubooru.func import pools as pool_func
        pool_func.sync_post_pools(post, pool_identifiers)
    if ctx.has_param("notes"):
        auth.verify_privilege(ctx.user, "posts:edit:notes")
        posts.update_post_notes(post, ctx.get_param_as_list("notes"))
    if ctx.has_param("flags"):
        auth.verify_privilege(ctx.user, "posts:edit:flags")
        posts.update_post_flags(post, ctx.get_param_as_string_list("flags"))
    if ctx.has_file("thumbnail"):
        auth.verify_privilege(ctx.user, "posts:edit:thumbnail")
        posts.update_post_thumbnail(post, ctx.get_file("thumbnail"))
    post.last_edit_time = datetime.utcnow()
    ctx.session.flush()
    snapshots.modify(post, ctx.user)
    ctx.session.commit()
    return _serialize_post(ctx, post)


@rest.routes.delete("/post/(?P<post_id>[^/]+)/?")
def delete_post(ctx: rest.Context, params: Dict[str, str]) -> rest.Response:
    post = _get_post(params, ctx.user)
    infix = "own" if ctx.user.user_id == post.user_id else "any"
    auth.verify_privilege(ctx.user, "posts:delete:%s" % infix)
    try:
        versions.verify_version(post, ctx)
    except errors.IntegrityError:
        # Version was bumped by background conversion (AVIF/Opus) —
        # re-fetch with the current version and retry once
        ctx.session.expire(post)
        post = _get_post(params, ctx.user)
    snapshots.delete(post, ctx.user)
    posts.delete(post)
    ctx.session.commit()
    return {}


@rest.routes.post("/post-merge/?")
def merge_posts(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    source_post_id = ctx.get_param_as_int("remove")
    target_post_id = ctx.get_param_as_int("mergeTo")
    source_post = posts.get_post_by_id(source_post_id, ctx.user)
    target_post = posts.get_post_by_id(target_post_id, ctx.user)
    replace_content = ctx.get_param_as_bool("replaceContent")
    versions.verify_version(source_post, ctx, "removeVersion")
    versions.verify_version(target_post, ctx, "mergeToVersion")
    versions.bump_version(target_post)
    auth.verify_privilege(ctx.user, "posts:merge")
    posts.merge_posts(source_post, target_post, replace_content)
    snapshots.merge(source_post, target_post, ctx.user)
    ctx.session.commit()
    return _serialize_post(ctx, target_post)


@rest.routes.get("/featured-post/?")
def get_featured_post(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    auth.verify_privilege(ctx.user, "posts:view:featured")
    post = posts.try_get_featured_post()
    return _serialize_post(ctx, post)


@rest.routes.post("/featured-post/?")
def set_featured_post(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    auth.verify_privilege(ctx.user, "posts:feature")
    post_id = ctx.get_param_as_int("id")
    post = posts.get_post_by_id(post_id, ctx.user)
    featured_post = posts.try_get_featured_post()
    if featured_post and featured_post.post_id == post.post_id:
        raise posts.PostAlreadyFeaturedError(
            "Post %r is already featured." % post_id
        )
    posts.feature_post(post, ctx.user)
    snapshots.modify(post, ctx.user)
    ctx.session.commit()
    return _serialize_post(ctx, post)


@rest.routes.put("/post/(?P<post_id>[^/]+)/score/?")
def set_post_score(ctx: rest.Context, params: Dict[str, str]) -> rest.Response:
    auth.verify_privilege(ctx.user, "posts:score")
    post = _get_post(params, ctx.user)
    score = ctx.get_param_as_int("score")
    scores.set_score(post, ctx.user, score)
    ctx.session.commit()
    return _serialize_post(ctx, post)


@rest.routes.delete("/post/(?P<post_id>[^/]+)/score/?")
def delete_post_score(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    auth.verify_privilege(ctx.user, "posts:score")
    post = _get_post(params, ctx.user)
    scores.delete_score(post, ctx.user)
    ctx.session.commit()
    return _serialize_post(ctx, post)


@rest.routes.post("/post/(?P<post_id>[^/]+)/favorite/?")
def add_post_to_favorites(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    auth.verify_privilege(ctx.user, "posts:favorite")
    post = _get_post(params, ctx.user)
    favorites.set_favorite(post, ctx.user)
    ctx.session.commit()
    return _serialize_post(ctx, post)


@rest.routes.delete("/post/(?P<post_id>[^/]+)/favorite/?")
def delete_post_from_favorites(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    auth.verify_privilege(ctx.user, "posts:favorite")
    post = _get_post(params, ctx.user)
    favorites.unset_favorite(post, ctx.user)
    ctx.session.commit()
    return _serialize_post(ctx, post)


@rest.routes.get("/post/(?P<post_id>[^/]+)/around/?")
def get_posts_around(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    auth.verify_privilege(ctx.user, "posts:list")
    _search_executor_config.user = ctx.user
    post_id = _get_post_id(params)
    return _search_executor.get_around_and_serialize(
        ctx, post_id, lambda post: _serialize_post(ctx, post)
    )


@rest.routes.post("/posts/reverse-search/?")
def get_posts_by_image(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    auth.verify_privilege(ctx.user, "posts:reverse_search")
    content = ctx.get_file("content")

    try:
        lookalikes = posts.search_by_image(content)
    except (errors.ThirdPartyError, errors.ProcessingError):
        lookalikes = []

    exact = posts.search_by_image_exact(content)
    return {
        "exactPost": _serialize_post(ctx, exact) if exact else None,
        "similarPosts": [
            {
                "distance": distance,
                "post": _serialize_post(ctx, post),
            }
            for distance, post in lookalikes
        ],
    }


@rest.routes.post("/post/(?P<post_id>[^/]+)/auto-tag/?")
def auto_tag_post(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    auth.verify_privilege(ctx.user, "posts:edit:tags")
    post_id = _get_post_id(params)
    post = posts.get_post_by_id(post_id, user=ctx.user)
    # Only the post owner can auto-tag
    if post.user_id != ctx.user.user_id:
        raise posts.PostAccessDeniedError(
            "Only the post owner can auto-tag their own posts."
        )
    try:
        from szurubooru.func import tagger
        # Try generated AVIF first (original may be deleted after conversion)
        if files.has(posts.get_post_avif_path(post)):
            content = files.get(posts.get_post_avif_path(post))
        else:
            content = files.get(posts.get_post_content_path(post))
        if not content:
            raise errors.ProcessingError("Post content not found on disk.")
        predicted = tagger.generate_tags(content)
        if not predicted:
            return {
                "post": _serialize_post(ctx, post),
                "tags": [],
                "added": 0,
                "message": "No tags predicted.",
            }
        tag_names = [t[0] for t in predicted]
        # Merge with existing tags (preserve manually-added tags)
        existing_names = [
            t.names[0].name if t.names else str(t.first_name)
            for t in post.tags
        ]
        all_names = list(set(existing_names) | set(tag_names))
        posts.update_post_tags(post, all_names)
        db.session.commit()
        return {
            "post": _serialize_post(ctx, post),
            "tags": [
                {"name": name, "confidence": round(conf, 3)}
                for name, conf in predicted
            ],
            "added": len(predicted),
        }
    except Exception as e:
        raise errors.ProcessingError(
            "Auto-tagging failed: %s" % str(e)
        )
