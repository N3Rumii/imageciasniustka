"use strict";

class PostBrowserView {
    constructor(posts, hasMore, loadMoreFn) {
        this._allPosts = posts || [];
        this._hasMore = hasMore || false;
        this._loadMoreFn = loadMoreFn || null;
        this._loadingMore = false;
        this._skipVideos = false;
        this._filteredPosts = [];
        this._startIndex = 0;
        this._autoplay = false;
        this._autoplayTimer = null;
        this._autoplayDelay = 3000;
        this._loaded = new Set();
        this._observer = null;
        this._currentIndex = 0;

        this._overlay = document.createElement("div");
        this._overlay.innerHTML =
            '<div class="browser-overlay" id="post-browser">' +
            '<div class="browser-topbar">' +
            '<span class="browser-title">Browse</span>' +
            '<span class="browser-counter" id="browser-counter">Loading...</span>' +
            '<div class="browser-controls">' +
            '<label class="browser-skip"><input type="checkbox" id="browser-skip-videos"> Skip videos</label>' +
            '<button class="browser-btn" id="browser-autoplay" title="Autoplay (Space)">▶</button>' +
            '<button class="browser-btn" id="browser-close" title="Close (Esc)">✕</button>' +
            '</div></div>' +
            '<div class="browser-images" id="browser-images">' +
            '<div class="browser-loading" id="browser-loading">Loading posts...</div>' +
            '</div>' +
            '<div class="browser-bottombar">' +
            '<span class="browser-hint">Scroll or ↑↓ to navigate | Space autoplay | Esc close</span>' +
            '</div></div>';
        document.body.appendChild(this._overlay);

        this._imagesEl = document.getElementById("browser-images");
        this._loadingEl = document.getElementById("browser-loading");
        this._counterEl = document.getElementById("browser-counter");
        this._autoplayBtn = document.getElementById("browser-autoplay");
        this._closeBtn = document.getElementById("browser-close");
        this._skipVideosCb = document.getElementById("browser-skip-videos");

        this._bindEvents();
        this._rebuild();

        document.body.style.overflow = "hidden";
    }

    _rebuild() {
        this._filteredPosts = this._skipVideos
            ? this._allPosts.filter((p) => p.type !== "video")
            : this._allPosts;

        if (this._observer) this._observer.disconnect();
        this._loaded.clear();
        this._wrappers = [];
        this._imagesEl.querySelectorAll(".browser-image-wrap").forEach((e) => e.remove());

        if (this._filteredPosts.length === 0) {
            this._loadingEl.style.display = "block";
            this._loadingEl.textContent = "No posts to browse.";
            this._counterEl.textContent = "0 / 0";
            return;
        }

        this._loadingEl.style.display = "none";

        for (let i = 0; i < this._filteredPosts.length; i++) {
            const post = this._filteredPosts[i];
            const wrap = document.createElement("div");
            wrap.className = "browser-image-wrap";
            wrap.setAttribute("data-index", i);

            if (post.type === "video") {
                const vid = document.createElement("video");
                vid.className = "browser-image";
                vid.controls = true;
                vid.preload = "none";
                vid.dataset.src = post.contentUrl;
                wrap.appendChild(vid);
            } else {
                const img = document.createElement("img");
                img.className = "browser-image";
                img.dataset.src = post.contentUrl;
                wrap.appendChild(img);
            }

            const label = document.createElement("span");
            label.className = "browser-image-id";
            label.textContent = "#" + post.id;
            wrap.appendChild(label);
            this._imagesEl.appendChild(wrap);
            this._wrappers.push(wrap);
        }

        this._observer = new IntersectionObserver(
            (entries) => {
                for (const entry of entries) {
                    if (entry.isIntersecting) {
                        const idx = parseInt(entry.target.getAttribute("data-index"));
                        this._loadMedia(idx);
                    }
                }
            },
            { rootMargin: "600px" }
        );

        for (const wrap of this._wrappers) {
            this._observer.observe(wrap);
        }

        this._currentIndex = 0;
        this._updateCounter();
    }

    _bindEvents() {
        this._closeBtn.addEventListener("click", () => this._close());
        this._autoplayBtn.addEventListener("click", () => this._toggleAutoplay());
        this._skipVideosCb.addEventListener("change", () => {
            this._skipVideos = this._skipVideosCb.checked;
            this._rebuild();
        });

        this._keyHandler = (e) => {
            if (e.key === "Escape") { e.preventDefault(); this._close(); }
            else if (e.key === " ") { e.preventDefault(); this._toggleAutoplay(); }
            else if (e.key === "ArrowDown" || e.key === "ArrowRight") { e.preventDefault(); this._scrollTo(this._currentIndex + 1); }
            else if (e.key === "ArrowUp" || e.key === "ArrowLeft") { e.preventDefault(); this._scrollTo(this._currentIndex - 1); }
        };
        document.addEventListener("keydown", this._keyHandler);

        this._scrollHandler = () => {
            this._updateVisibleIndex();
            this._checkLoadMore();
        };
        this._imagesEl.addEventListener("scroll", this._scrollHandler);
    }

    _checkLoadMore() {
        if (!this._hasMore || this._loadingMore || !this._loadMoreFn) return;
        if (this._imagesEl.scrollTop + this._imagesEl.clientHeight >=
            this._imagesEl.scrollHeight - 600) {
            this._loadingMore = true;
            this._loadMoreFn((newPosts, hasMore) => {
                this._allPosts = this._allPosts.concat(newPosts);
                this._hasMore = hasMore;
                this._loadingMore = false;
                this._appendNewPosts(newPosts);
            });
        }
    }

    _appendNewPosts(newPosts) {
        // Update both allPosts and filteredPosts so counter stays correct
        this._filteredPosts = this._skipVideos
            ? this._allPosts.filter((p) => p.type !== "video")
            : this._allPosts;
        const startIndex = this._wrappers.length;
        for (let i = 0; i < newPosts.length; i++) {
            const post = newPosts[i];
            const idx = startIndex + i;
            const wrap = document.createElement("div");
            wrap.className = "browser-image-wrap";
            wrap.setAttribute("data-index", idx);

            if (post.type === "video") {
                const vid = document.createElement("video");
                vid.className = "browser-image";
                vid.controls = true;
                vid.preload = "none";
                vid.dataset.src = post.contentUrl;
                wrap.appendChild(vid);
            } else {
                const img = document.createElement("img");
                img.className = "browser-image";
                img.dataset.src = post.contentUrl;
                wrap.appendChild(img);
            }

            const label = document.createElement("span");
            label.className = "browser-image-id";
            label.textContent = "#" + post.id;
            wrap.appendChild(label);
            this._imagesEl.appendChild(wrap);
            this._wrappers.push(wrap);
            this._observer.observe(wrap);
        }
        this._updateCounter();
    }

    _loadMedia(index) {
        if (this._loaded.has(index)) return;
        this._loaded.add(index);
        const wrap = this._wrappers[index];
        if (!wrap) return;
        const el = wrap.querySelector("img, video");
        if (el && el.dataset.src) {
            el.src = el.dataset.src;
            el.onload = el.onloadeddata = () => el.removeAttribute("data-src");
        }
    }

    _scrollTo(index) {
        if (index < 0 || index >= this._wrappers.length) return;
        this._wrappers[index].scrollIntoView({ behavior: "smooth", block: "start" });
    }

    _updateVisibleIndex() {
        if (this._wrappers.length === 0) return;
        const containerRect = this._imagesEl.getBoundingClientRect();
        const midY = containerRect.top + containerRect.height * 0.3;
        let closest = 0, closestDist = Infinity;
        for (let i = 0; i < this._wrappers.length; i++) {
            const rect = this._wrappers[i].getBoundingClientRect();
            const dist = Math.abs(rect.top + rect.height / 2 - midY);
            if (dist < closestDist) { closestDist = dist; closest = i; }
        }
        this._currentIndex = closest;
        this._updateCounter();
    }

    _updateCounter() {
        this._counterEl.textContent = (this._currentIndex + 1) + " / " + this._filteredPosts.length;
    }

    _toggleAutoplay() {
        this._autoplay = !this._autoplay;
        this._autoplayBtn.classList.toggle("active", this._autoplay);
        this._autoplayBtn.textContent = this._autoplay ? "⏸" : "▶";
        this._autoplay ? this._startAutoplay() : this._stopAutoplay();
    }

    _startAutoplay() {
        this._stopAutoplay();
        this._autoplayTimer = setInterval(() => this._scrollTo((this._currentIndex || 0) + 1), this._autoplayDelay);
    }

    _stopAutoplay() {
        if (this._autoplayTimer) { clearInterval(this._autoplayTimer); this._autoplayTimer = null; }
    }

    _close() {
        this._stopAutoplay();
        if (this._observer) this._observer.disconnect();
        document.removeEventListener("keydown", this._keyHandler);
        if (this._imagesEl) this._imagesEl.removeEventListener("scroll", this._scrollHandler);
        document.body.style.overflow = "";
        if (this._overlay && this._overlay.parentNode) this._overlay.parentNode.removeChild(this._overlay);
    }
}

module.exports = PostBrowserView;
