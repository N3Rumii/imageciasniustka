"""Batch resize + AVIF conversion for posts 271-639."""
import os, sys, time
os.chdir('/data/data/com.termux/files/home/hosting_cias/server')

from szurubooru import config, db
from szurubooru.model import post as pm
from szurubooru.func import posts, files, images

done = 0
skipped = 0
errors = 0
start = time.time()

for pid in range(271, 640):
    try:
        post = db.session.query(pm.Post).get(pid)
        if not post:
            continue
        if post.type not in (pm.Post.TYPE_IMAGE, pm.Post.TYPE_ANIMATION):
            continue

        # Get content: prefer existing AVIF, fall back to original
        avif_path = posts.get_post_avif_path(post)
        orig_path = posts.get_post_content_path(post)
        content = None
        already_avif = False

        if files.has(avif_path):
            content = files.get(avif_path)
            already_avif = True
        elif files.has(orig_path):
            content = files.get(orig_path)
        else:
            continue

        if len(content) < 100:
            continue

        # Decode + resize
        img = images.Image(content)
        new_w = max(1, int(img.width * 0.6))
        new_h = max(1, int(img.height * 0.6))
        img.resize_fill(new_w, new_h)
        avif_data = img.to_avif(quality=40, effort=4)

        # Save AVIF (overwrite or create)
        files.save(avif_path, avif_data)
        post.file_size = len(avif_data)
        post.canvas_width = img.width
        post.canvas_height = img.height
        if not already_avif:
            setattr(post, '_original_mime_type', post.mime_type)
            post.mime_type = 'image/avif'
            # Also regenerate thumbnail
            thumb = images.Image(avif_data)
            thumb.resize_fill(300, 300)
            files.save(posts.get_post_thumbnail_path(post),
                       thumb.to_avif(quality=50, effort=4))

        db.session.commit()
        done += 1

    except Exception as e:
        db.session.rollback()
        errors += 1
        if errors <= 5:
            print(f'  ✗ #{pid}: {str(e)[:80]}')

    # Progress every 30 posts
    if (done + errors) % 30 == 0:
        elapsed = time.time() - start
        rate = (done + errors) / elapsed * 60
        print(f'  ... {done} resized, {errors} errors ({rate:.0f}/min)')

elapsed = time.time() - start
print(f'\nDone: {done} resized, {errors} errors in {elapsed:.0f}s')
print(f'New AVIF conversions: {sum(1 for _ in [])}')
