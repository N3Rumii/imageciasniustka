"use strict";

const events = require("../events.js");
const views = require("../util/views.js");
const api = require("../api.js");
const uri = require("../util/uri.js");
const Status = require("../models/status.js");
const StatusMiniView = require("./status_mini_view.js");
const PostList = require("../models/post_list.js");

const template = views.getTemplate("user-profile");

class UserProfileView extends events.EventTarget {
    constructor(user) {
        super();
        this._user = user;
        this._hostNode = document.getElementById("content-holder");
        this._feedItems = [];
        this._allItems = [];
        this._activeTab = "blog";

        this._render();
        this._loadFeed();
    }

    _render() {
        var self = this;
        var ctx = {
            user: this._user,
            profileBio: this._user.profileBio,
            profileAbout: this._user.profileAbout,
            profileLinks: this._user.profileLinks,
            profileCss: this._user.profileCss,
            profileHeaderUrl: this._user.profileHeaderUrl,
            profileAccentColor: this._user.profileAccentColor,
            profileLayout: this._user.profileLayout,
            canFollow: api.isLoggedIn() && api.userName &&
                api.userName.toLowerCase() !== this._user.name.toLowerCase(),
            isOwnProfile: api.isLoggedIn() && api.userName &&
                api.userName.toLowerCase() === this._user.name.toLowerCase(),
            feedItems: this._feedItems,
            formatClientLink: function() {
                return uri.formatClientLink.apply(null, arguments);
            },
            makeRelativeTime: function(time) {
                if (!time) return "";
                var diff = Date.now() - new Date(time).getTime();
                var seconds = Math.floor(diff / 1000);
                if (seconds < 60) return "just now";
                if (seconds < 3600) return Math.floor(seconds / 60) + "m ago";
                if (seconds < 86400) return Math.floor(seconds / 3600) + "h ago";
                if (seconds < 604800) return Math.floor(seconds / 86400) + "d ago";
                return new Date(time).toLocaleDateString();
            },
            makeThumbnail: views.makeThumbnail,
        };
        views.replaceContent(this._hostNode, template(ctx));
        this._renderFeedItems();
        this._wireEvents();

        // Inject custom CSS into page head
        var css = this._user.profileCss;
        var oldStyle = document.getElementById("user-custom-css");
        if (oldStyle) oldStyle.remove();
        if (css) {
            var styleEl = document.createElement("style");
            styleEl.id = "user-custom-css";
            styleEl.textContent = css;
            document.head.appendChild(styleEl);
        }
    }

    _wireEvents() {
        var self = this;

        // Tab switching
        var tabs = this._hostNode.querySelectorAll(".profile-tab");
        for (var i = 0; i < tabs.length; i++) {
            tabs[i].addEventListener("click", function() {
                var tab = this.getAttribute("data-tab");
                for (var j = 0; j < tabs.length; j++) tabs[j].classList.remove("active");
                this.classList.add("active");
                self._activeTab = tab;
                self._renderFeed();
            });
        }

        // Profile composer
        var composerInput = this._hostNode.querySelector(".profile-composer-input");
        var composerSend = this._hostNode.querySelector(".profile-composer-send");
        var fileInput = this._hostNode.querySelector(".profile-composer-file");
        if (composerSend) {
            composerSend.addEventListener("click", function() {
                self._handleCompose();
            });
            composerInput.addEventListener("input", function() {
                var count = self._hostNode.querySelector(".profile-composer-count");
                if (count) count.textContent = composerInput.value.length + " / 3000";
            });
            composerInput.addEventListener("keydown", function(e) {
                if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault();
                    self._handleCompose();
                }
            });
        }
        if (fileInput) {
            fileInput.addEventListener("change", function() {
                var attachLabel = self._hostNode.querySelector(".profile-composer-attach");
                if (fileInput.files.length > 0) {
                    var name = fileInput.files[0].name;
                    if (name.length > 20) name = name.substring(0, 18) + "...";
                    if (attachLabel) attachLabel.setAttribute("data-file", name);
                    composerInput.placeholder = "Add a caption...";
                } else {
                    if (attachLabel) attachLabel.removeAttribute("data-file");
                    composerInput.placeholder = "Write a blog post...";
                }
            });
        }

        // Follow button
        var followBtn = this._hostNode.querySelector(".follow-btn");
        if (followBtn) {
            followBtn.addEventListener("click", function() {
                self._toggleFollow();
            });
        }

        // Stat clicks
        var statClicks = this._hostNode.querySelectorAll(".stat-clickable");
        for (var i = 0; i < statClicks.length; i++) {
            statClicks[i].addEventListener("click", function() {
                var action = this.getAttribute("data-action");
                self.dispatchEvent(new CustomEvent("statClick", { detail: { action: action } }));
            });
        }


    }

    _toggleFollow() {
        var self = this;
        var promise = this._user.isFollowing
            ? this._user.unfollow()
            : this._user.follow();
        promise.then(function() { self._render(); })
            .catch(function(err) {
                self.dispatchEvent(new CustomEvent("error", { detail: { message: err.message } }));
            });
    }

    _handleCompose() {
        var self = this;
        var input = this._hostNode.querySelector(".profile-composer-input");
        var sendBtn = this._hostNode.querySelector(".profile-composer-send");
        var fileInput = this._hostNode.querySelector(".profile-composer-file");
        var attachLabel = this._hostNode.querySelector(".profile-composer-attach");
        var text = input.value.trim();
        var file = fileInput && fileInput.files.length > 0 ? fileInput.files[0] : null;
        if (!text && !file) return;
        if (text.length > 3000) {
            self.showError("Blog posts are limited to 3000 characters.");
            return;
        }

        sendBtn.disabled = true;
        input.disabled = true;

        // Build detail - text is null if empty but file present
        var postText = text || (file ? "" : null);
        Status.create(postText, file || undefined, null, false, "blog")
            .then(function(newStatus) {
                input.value = "";
                if (fileInput) fileInput.value = "";
                if (attachLabel) attachLabel.removeAttribute("data-file");
                sendBtn.disabled = false;
                input.disabled = false;
                // Force postType to be blog (defensive)
                newStatus._postType = "blog";
                self._allItems.unshift(newStatus);
                if (self._activeTab === "blog") {
                    self._feedItems.unshift(newStatus);
                    // Just append the new item to the feed DOM directly
                    var feed = self._hostNode.querySelector(".profile-feed");
                    if (feed) {
                        var empty = feed.querySelector(".profile-feed-empty");
                        if (empty) empty.style.display = "none";
                        var wrapper = document.createElement("div");
                        wrapper.className = "profile-feed-item";
                        var canEdit = api.isLoggedIn() && api.userName &&
                            (newStatus.user && newStatus.user.name && api.userName.toLowerCase() === newStatus.user.name.toLowerCase());
                        var miniView = new StatusMiniView(newStatus, {
                            canEditStatus: canEdit ? function() { return true; } : null,
                            canDeleteStatus: canEdit ? function() { return true; } : null,
                        });
                        wrapper.appendChild(miniView.hostNode);
                        feed.insertBefore(wrapper, feed.firstChild);
                        // Wire events on the new mini view
                        (function(mv) {
                            mv.addEventListener("delete", function(e) {
                                if (confirm("Delete this post?")) {
                                    e.detail.status.delete().then(function() {
                                        self._allItems = self._allItems.filter(function(r) { return r.id !== newStatus.id; });
                                        self._feedItems = self._feedItems.filter(function(r) { return r.id !== newStatus.id; });
                                        wrapper.remove();
                                        if (self._feedItems.length === 0 && empty) empty.style.display = "";
                                    }).catch(function(err) { self.showError(err.message); });
                                }
                            });
                            mv.addEventListener("edit", function(e) {
                                for (var j = 0; j < self._allItems.length; j++) {
                                    if (self._allItems[j].id === e.detail.status.id) self._allItems[j] = e.detail.status;
                                }
                                for (var j = 0; j < self._feedItems.length; j++) {
                                    if (self._feedItems[j].id === e.detail.status.id) self._feedItems[j] = e.detail.status;
                                }
                            });
                        })(miniView);
                    }
                }
                self.showSuccess("Posted!");
            })
            .catch(function(err) {
                sendBtn.disabled = false;
                input.disabled = false;
                self.showError(err.message);
            });
    }

    _loadFeed() {
        var self = this;
        Status.getTimeline({ user: this._user.name, limit: 50 })
            .then(function(statuses) {
                self._allItems = statuses;
                self._renderFeed();
            })
            .catch(function(err) {
                self._allItems = [];
                self._renderFeed();
            });
    }

    _renderFeedItems() {
        var feed = this._hostNode.querySelector(".profile-feed");
        if (!feed) return;
        // Clear existing items and any leftover media buttons
        var oldItems = feed.querySelectorAll(".profile-feed-item, .profile-view-more-btn");
        for (var i = 0; i < oldItems.length; i++) oldItems[i].remove();
        var empty = feed.querySelector(".profile-feed-empty");
        if (empty) empty.style.display = "none";

        if (!this._feedItems || this._feedItems.length === 0) {
            if (empty) empty.style.display = "";
            return;
        }

        for (var i = 0; i < this._feedItems.length; i++) {
            var item = this._feedItems[i];
            var wrapper = document.createElement("div");
            wrapper.className = "profile-feed-item";
            var canEdit = api.isLoggedIn() && api.userName &&
                api.userName.toLowerCase() === (item.user && item.user.name ? item.user.name.toLowerCase() : "");
            var miniView = new StatusMiniView(item, {
                canEditStatus: canEdit ? function() { return true; } : null,
                canDeleteStatus: canEdit ? function() { return true; } : null,
                onReply: function(s) {
                    var router = require("../router.js");
                    var uri = require("../util/uri.js");
                    router.show(uri.formatClientLink("status", s.id));
                },
                onFavorite: function(s) {
                    var p = s.ownFavorite ? s.unfavorite() : s.favorite();
                    p.catch(function(err) { /* silent */ });
                },
                onRepost: function(s) {
                    s.undoRepost().then(function() {}).catch(function() {});
                },
                onRepostWithText: function(s, text) {
                    s.repost(text).then(function() {}).catch(function() {});
                },
            });
            // Wire delete and edit events for profile feed
            (function(miniView, item, wrapper) {
                miniView.addEventListener("delete", function(e) {
                    var toDelete = e.detail.status;
                    if (confirm("Delete this post?")) {
                        toDelete.delete().then(function() {
                            self._allItems = self._allItems.filter(function(r) { return r.id !== toDelete.id; });
                            self._renderFeed();
                            self.showSuccess("Deleted!");
                        }).catch(function(err) {
                            self.showError(err.message);
                        });
                    }
                });
                miniView.addEventListener("edit", function(e) {
                    var edited = e.detail.status;
                    for (var j = 0; j < self._allItems.length; j++) {
                        if (self._allItems[j].id === edited.id) {
                            self._allItems[j] = edited;
                            break;
                        }
                    }
                    self._renderFeed();
                });
            })(miniView, item, wrapper);
            wrapper.appendChild(miniView.hostNode);
            feed.appendChild(wrapper);
        }
    }

    _renderFeed() {
        var tab = this._activeTab || "blog";
        // Show/hide composer based on tab
        var composer = this._hostNode.querySelector(".profile-composer");
        if (composer) composer.style.display = (tab === "blog") ? "" : "none";

        // Clear feed immediately so old content doesn't bleed
        var feed = this._hostNode.querySelector(".profile-feed");
        if (feed) {
            var old = feed.querySelectorAll(".profile-feed-item, .profile-view-more-btn");
            for (var i = 0; i < old.length; i++) old[i].remove();
            var empty = feed.querySelector(".profile-feed-empty");
            if (empty) empty.style.display = "";
        }

        if (tab === "blog") {
            this._feedItems = this._allItems.filter(function(s) { return s.postType === "blog"; });
        } else if (tab === "statuses") {
            this._feedItems = this._allItems.filter(function(s) { return !s.postType || s.postType === "status"; });
        } else if (tab === "media") {
            this._loadMediaTab();
            return;
        }
        this._feedItems = this._feedItems || [];
        this._renderFeedItems();
    }

    _loadMediaTab() {
        var self = this;
        // Don't restrict fields — get full post data so thumbnailUrl is populated
        PostList.search("submit:" + this._user.name, 0, 3, []).then(function(response) {
            self._mediaItems = (response.results || []).map(function(p) {
                return {
                    id: p.id,
                    thumbnailUrl: p.thumbnailUrl || "",
                    contentUrl: p.contentUrl || ""
                };
            });
            self._renderMediaTab();
        }).catch(function(err) {
            self._mediaItems = [];
            self._renderMediaTab();
        });
    }

    _renderMediaTab() {
        var feed = this._hostNode.querySelector(".profile-feed");
        if (!feed) return;
        // Clear everything except the empty-state div
        while (feed.firstChild) {
            if (feed.firstChild.classList && feed.firstChild.classList.contains("profile-feed-empty")) break;
            feed.removeChild(feed.firstChild);
        }
        // Remove any leftover view-more buttons
        var oldBtns = feed.querySelectorAll(".profile-view-more-btn");
        for (var i = 0; i < oldBtns.length; i++) oldBtns[i].remove();
        var empty = feed.querySelector(".profile-feed-empty");
        if (empty) empty.style.display = "none";

        if (!this._mediaItems || this._mediaItems.length === 0) {
            if (empty) { empty.style.display = ""; empty.querySelector("p").textContent = "No media yet."; }
            return;
        }

        for (var i = 0; i < this._mediaItems.length; i++) {
            var post = this._mediaItems[i];
            var wrapper = document.createElement("div");
            wrapper.className = "profile-feed-item profile-media-item";
            var uri = require("../util/uri.js");
            var link = uri.formatClientLink("post", post.id);
            wrapper.innerHTML =
                '<a href="' + link + '" class="profile-media-thumb">' +
                '<img src="' + (post.thumbnailUrl || "") + '" alt="Post #' + post.id + '"/>' +
                '</a>';
            feed.appendChild(wrapper);
        }

        // Add "View more" button
        var moreBtn = document.createElement("a");
        moreBtn.className = "profile-view-more-btn";
        var uri2 = require("../util/uri.js");
        moreBtn.href = uri2.formatClientLink("posts", { query: "submit:" + this._user.name });
        moreBtn.textContent = "View all media →";
        feed.appendChild(moreBtn);
    }

    showSuccess(msg) {
        views.showSuccess(this._hostNode, msg);
    }

    showError(msg) {
        views.showError(this._hostNode, msg);
    }
}

module.exports = UserProfileView;
