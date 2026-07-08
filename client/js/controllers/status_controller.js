"use strict";

const router = require("../router.js");
const api = require("../api.js");
const uri = require("../util/uri.js");
const topNavigation = require("../models/top_navigation.js");
const Status = require("../models/status.js");
const StatusComposerView = require("../views/status_composer_view.js");
const StatusTimelineView = require("../views/status_timeline_view.js");
const StatusMiniView = require("../views/status_mini_view.js");

class StatusController {
    constructor(ctx) {
        topNavigation.activate("community");
        topNavigation.setTitle("Community");

        this._ctx = ctx;
        this._feed = "everything";
        this._sort = "";
        // Read tag from URL query string
        this._tag = "";
        if (window.location.search) {
            var params = new URLSearchParams(window.location.search);
            this._tag = params.get("tag") || "";
        }
        this._statusViews = [];

        this._view = new StatusTimelineView();
        this._hostNode = this._view.getHostNode();
        this._listNode = this._hostNode.querySelector(".status-list");

        this._bindTabs();
        this._bindSort();
        this._setupComposer();
        this._updateTagUI();
        this._loadTimeline(true);

        // Infinite scroll: load more when approaching bottom
        var self = this;
        this._scrollHandler = function() {
            var scrollY = window.scrollY || window.pageYOffset;
            var windowH = window.innerHeight;
            var docH = document.documentElement.scrollHeight;
            if (docH - scrollY - windowH < 400) {
                self._loadTimeline(false);
            }
        };
        window.addEventListener("scroll", this._scrollHandler, { passive: true });
    }

    _buildQuery() {
        return "";
    }

    _buildParams() {
        var params = {};
        if (this._feed === "myfeed") params.feed = "myfeed";
        if (this._sort) params.sort = this._sort;
        if (this._tag) params.tag = this._tag;
        return params;
    }

    _bindTabs() {
        var self = this;
        var tabs = this._hostNode.querySelectorAll(".feed-tab");
        for (var i = 0; i < tabs.length; i++) {
            tabs[i].addEventListener("click", function(e) {
                e.preventDefault();
                self._feed = this.getAttribute("data-feed");
                self._tag = ""; // Clear tag filter
                for (var j = 0; j < tabs.length; j++) tabs[j].classList.remove("active");
                this.classList.add("active");
                self._updateTagUI();
                self._loadTimeline(true);
            });
        }
    }

    _bindSort() {
        var self = this;
        var btns = this._hostNode.querySelectorAll(".sort-btn");
        for (var i = 0; i < btns.length; i++) {
            btns[i].addEventListener("click", function(e) {
                e.preventDefault();
                var base = this.getAttribute("data-sort-base");
                if (base) {
                    // Toggle: inactive → desc → asc → inactive
                    if (!self._sort || self._sort.indexOf(base) !== 0) {
                        self._sort = base; // first click: descending
                    } else if (self._sort === base) {
                        self._sort = base + ",asc"; // second click: ascending
                    } else {
                        self._sort = ""; // third click: clear
                    }
                } else {
                    // Clear button
                    self._sort = "";
                }
                self._updateSortUI();
                self._loadTimeline(true);
            });
        }
    }

    _updateTagUI() {
        var bar = this._hostNode.querySelector(".tag-filter-bar");
        if (this._tag) {
            if (!bar) {
                bar = document.createElement("div");
                bar.className = "tag-filter-bar";
                var sortBar = this._hostNode.querySelector(".sort-bar");
                if (sortBar && sortBar.parentNode) {
                    sortBar.parentNode.insertBefore(bar, sortBar);
                }
            }
            bar.innerHTML =
                '<span>Filter: <strong>#' + this._tag + '</strong></span>' +
                ' <a href="#" class="tag-filter-clear">✕ clear</a>';
            bar.querySelector(".tag-filter-clear").addEventListener("click", function(e) {
                e.preventDefault();
                this._tag = "";
                this._updateTagUI();
                this._loadTimeline();
            }.bind(this));
        } else if (bar) {
            bar.remove();
        }
    }

    _updateSortUI() {
        var btns = this._hostNode.querySelectorAll(".sort-btn");
        for (var i = 0; i < btns.length; i++) {
            var btn = btns[i];
            btn.classList.remove("active");
            var base = btn.getAttribute("data-sort-base");
            if (base && this._sort && this._sort.indexOf(base) === 0) {
                btn.classList.add("active");
                var dirEl = btn.querySelector(".sort-dir");
                if (dirEl) {
                    dirEl.textContent = this._sort.indexOf(",asc") >= 0 ? "↑" : "↓";
                }
            }
        }
    }

    _setupComposer() {
        var container = this._hostNode.querySelector(".status-composer-container");
        if (!container) return;
        try {
            this._composerView = new StatusComposerView({ hostNode: container });
            var self = this;
            this._composerView.addEventListener("submit", function(e) {
                self._handleCompose(e);
            });
        } catch(e) {
            // ignore composer errors
        }
    }

    _handleCompose(e) {
        var self = this;
        var detail = e.detail;
        // Clear previous messages and disable submit to prevent spam
        self._view.clearMessages();
        var submitBtn = self._hostNode.querySelector(".status-composer-submit");
        if (submitBtn) submitBtn.disabled = true;
        Status.create(detail.text || "", detail.file, detail.parentId)
            .then(function(status) {
                self._prependStatus(status);
                self._setupComposer();
                self._view.showSuccess("Posted!");
            })
            .catch(function(err) {
                if (submitBtn) submitBtn.disabled = false;
                self._view.showError(err.message);
            });
    }

    _prependStatus(status) {
        var self = this;
        var canEdit = api.isLoggedIn() && api.userName && api.userName.toLowerCase() === (status.user && status.user.name ? status.user.name.toLowerCase() : "");
        var miniView = new StatusMiniView(status, {
            canEditStatus: canEdit ? function() { return true; } : null,
            canDeleteStatus: canEdit ? function() { return true; } : null,
            onReply: function(s) { router.show(uri.formatClientLink("status", s.id)); },
            onFavorite: function(s) {
                var p = s.ownFavorite ? s.unfavorite() : s.favorite();
                p.catch(function(err) { self._view.showError(err.message); });
            },
            onRepost: function(s) {
                // Only called for undo (already reposted)
                s.undoRepost().then(function() {
                    self._view.showSuccess("Repost removed.");
                    self._loadTimeline();
                }).catch(function(err) { self._view.showError(err.message); });
            },
            onRepostWithText: function(s, text) {
                s.repost(text).then(function() {
                    self._view.showSuccess("Reposted!");
                    self._loadTimeline();
                }).catch(function(err) { self._view.showError(err.message); });
            },
            onEdit: function(s) {
                // Handled internally by StatusMiniView._startEdit()
            },
            onDelete: function(s) {
                if (confirm("Delete?")) {
                    s.delete().then(function() { self._view.showSuccess("Deleted!"); self._loadTimeline(); })
                        .catch(function(err) { self._view.showError(err.message); });
                }
            },
        });
        this._statusViews.unshift(miniView);
        if (this._listNode.firstChild) {
            this._listNode.insertBefore(miniView._hostNode, this._listNode.firstChild);
        } else {
            this._listNode.appendChild(miniView._hostNode);
        }
        // remove empty message
        var empty = this._listNode.querySelector(".status-empty");
        if (empty) empty.remove();
        this._wireMiniView(miniView);
    }

    _loadTimeline(reset) {
        var self = this;
        if (reset) {
            this._timelineOffset = 0;
            this._timelineDone = false;
            this._timelineLoading = false;
        }
        if (this._timelineLoading || this._timelineDone) return;
        this._timelineLoading = true;

        var params = this._buildParams();
        params.offset = this._timelineOffset || 0;
        params.limit = 25;

        Status.getTimeline(params)
            .then(function(statuses) {
                self._timelineLoading = false;
                // Count only top-level posts (not replies) to decide if done
                var parents = statuses.filter(function(s) { return !s.isReply; });
                if (parents.length < 8) self._timelineDone = true;
                self._timelineOffset = (self._timelineOffset || 0) + statuses.length;
                if (reset) {
                    self._renderStatuses(statuses);
                } else {
                    self._appendStatuses(statuses);
                }
            })
            .catch(function(err) {
                self._timelineLoading = false;
                self._view.showError(err.message);
            });
    }

    _appendStatuses(statuses) {
        if (!statuses || statuses.length === 0) return;

        var self = this;
        // Filter replies out, group under parents
        var parents = [];
        var replyMap = {};
        for (var i = 0; i < statuses.length; i++) {
            var s = statuses[i];
            if (s.isReply && s.replyTo && s.replyTo.id) {
                var pid = s.replyTo.id;
                if (!replyMap[pid]) replyMap[pid] = [];
                replyMap[pid].push(s);
            } else {
                parents.push(s);
            }
        }

        for (var i = 0; i < parents.length; i++) {
            var status = parents[i];
            var canEdit = api.isLoggedIn() && api.userName && api.userName.toLowerCase() === (status.user && status.user.name ? status.user.name.toLowerCase() : "");
            var miniView = new StatusMiniView(status, {
                canEditStatus: canEdit ? function() { return true; } : null,
                canDeleteStatus: canEdit ? function() { return true; } : null,
                onReply: function(s) { router.show(uri.formatClientLink("status", s.id)); },
                onFavorite: function(s) {
                    var p = s.ownFavorite ? s.unfavorite() : s.favorite();
                    p.catch(function(err) { self._view.showError(err.message); });
                },
                onRepost: function(s) {
                    s.undoRepost().then(function() {
                        self._view.showSuccess("Repost removed.");
                    }).catch(function(err) { self._view.showError(err.message); });
                },
                onRepostWithText: function(s, text) {
                    s.repost(text).then(function() {
                        self._view.showSuccess("Reposted!");
                    }).catch(function(err) { self._view.showError(err.message); });
                },
            });
            this._statusViews.push(miniView);
            this._listNode.appendChild(miniView._hostNode);
            this._wireMiniView(miniView);

            var childReplies = replyMap[status.id] || [];
            if (childReplies.length > 0 || status.replyCount > 0) {
                var threadSection = self._buildThreadSection(status, childReplies);
                this._listNode.appendChild(threadSection);
            }
        }
    }

    _renderStatuses(statuses) {
        this._statusViews = [];
        this._listNode.innerHTML = "";
        this._repliesCache = this._repliesCache || {};

        if (!statuses || statuses.length === 0) {
            this._listNode.innerHTML = '<div class="status-empty"><p>No statuses yet. Be the first!</p></div>';
            return;
        }

        var self = this;

        // Separate parents (top-level posts) from replies
        var parents = [];
        var replyMap = {};
        for (var i = 0; i < statuses.length; i++) {
            var s = statuses[i];
            if (s.isReply && s.replyTo && s.replyTo.id) {
                var pid = s.replyTo.id;
                if (!replyMap[pid]) replyMap[pid] = [];
                replyMap[pid].push(s);
            } else {
                parents.push(s);
            }
        }

        // Re-sort replies by creation time ascending (oldest first)
        for (var pid in replyMap) {
            replyMap[pid].sort(function(a, b) {
                return new Date(a.creationTime) - new Date(b.creationTime);
            });
        }

        for (var i = 0; i < parents.length; i++) {
            var status = parents[i];
            var canEdit = api.isLoggedIn() && api.userName && api.userName.toLowerCase() === (status.user && status.user.name ? status.user.name.toLowerCase() : "");
            var miniView = new StatusMiniView(status, {
                canEditStatus: canEdit ? function() { return true; } : null,
                canDeleteStatus: canEdit ? function() { return true; } : null,
                onReply: function(s) { router.show(uri.formatClientLink("status", s.id)); },
                onFavorite: function(s) {
                    var p = s.ownFavorite ? s.unfavorite() : s.favorite();
                    p.catch(function(err) { self._view.showError(err.message); });
                },
                onRepost: function(s) {
                    s.undoRepost().then(function() {
                        self._view.showSuccess("Repost removed.");
                    }).catch(function(err) { self._view.showError(err.message); });
                },
                onRepostWithText: function(s, text) {
                    s.repost(text).then(function() {
                        self._view.showSuccess("Reposted!");
                    }).catch(function(err) { self._view.showError(err.message); });
                },
            });
            this._statusViews.push(miniView);
            this._listNode.appendChild(miniView._hostNode);
            this._wireMiniView(miniView);

            // Build collapsible thread section from flat-list replies
            var childReplies = replyMap[status.id] || [];
            var replyCount = childReplies.length || status.replyCount || 0;

            // Always render the divider if there are replies (from flat list OR count says so)
            if (replyCount > 0) {
                var threadSection = self._buildThreadSection(status, childReplies);
                this._listNode.appendChild(threadSection);
            }
        }
    }

    _buildThreadSection(parentStatus, existingReplies) {
        var self = this;

        var section = document.createElement("div");
        section.className = "thread-section";
        section.setAttribute("data-parent-id", parentStatus.id);

        var replyCount = existingReplies.length || parentStatus.replyCount || 0;

        // Collapsible divider
        var divider = document.createElement("div");
        divider.className = "response-divider";
        divider.innerHTML = '<span class="response-divider-label">💬 ' + replyCount + ' Response' + (replyCount !== 1 ? 's' : '') + '</span>';
        section.appendChild(divider);

        // Expandable content wrapper
        var content = document.createElement("div");
        content.className = "thread-content";
        content.style.maxHeight = "0";
        content.style.overflow = "hidden";
        content.style.opacity = "0";
        content.style.transition = "max-height 200ms ease, opacity 200ms ease";
        section.appendChild(content);

        // Replies container
        var repliesContainer = document.createElement("div");
        repliesContainer.className = "thread-replies";
        content.appendChild(repliesContainer);

        // Inline composer
        var composer = document.createElement("div");
        composer.className = "thread-composer";
        composer.innerHTML =
            '<textarea class="thread-composer-input" rows="1" placeholder="Write a reply..." maxlength="1000"></textarea>' +
            '<button class="thread-composer-send">Send</button>';
        content.appendChild(composer);

        // Wire divider click — expand/collapse with animation
        divider.addEventListener("click", function() {
            self._handleThreadToggle(parentStatus, section, divider, content, repliesContainer, composer);
        });

        // Wire inline composer
        var input = composer.querySelector(".thread-composer-input");
        var sendBtn = composer.querySelector(".thread-composer-send");
        sendBtn.addEventListener("click", function() {
            self._handleThreadCompose(parentStatus, input, sendBtn, section, divider, content, repliesContainer, composer);
        });
        input.addEventListener("keydown", function(e) {
            if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                sendBtn.click();
            }
        });

        // Auto-resize textarea
        input.addEventListener("input", function() {
            this.style.height = "auto";
            this.style.height = Math.min(this.scrollHeight, 120) + "px";
        });

        return section;
    }

    _handleThreadToggle(parentStatus, section, divider, content, repliesContainer, composer) {
        var self = this;
        var isExpanded = content.style.maxHeight !== "0px" && content.style.maxHeight !== "0";

        if (isExpanded) {
            // Collapse
            content.style.maxHeight = "0";
            content.style.opacity = "0";
            divider.classList.remove("expanded");
            var cachedCount = (self._repliesCache[parentStatus.id] && self._repliesCache[parentStatus.id].length) || repliesContainer.children.length || parentStatus.replyCount || 0;
            var label = divider.querySelector(".response-divider-label");
            if (label) label.textContent = '💬 ' + cachedCount + ' Response' + (cachedCount !== 1 ? 's' : '');
        } else {
            // Expand — load replies if needed
            divider.classList.add("expanded");

            if (repliesContainer.children.length === 0) {
                var cached = self._repliesCache[parentStatus.id];
                if (cached && cached.length > 0) {
                    self._renderReplies(cached, repliesContainer, parentStatus.id);
                    self._finalizeExpand(content, divider, parentStatus, cached.length);
                } else {
                    parentStatus.getReplies().then(function(replies) {
                        self._repliesCache[parentStatus.id] = replies;
                        repliesContainer.innerHTML = "";
                        self._renderReplies(replies, repliesContainer, parentStatus.id);
                        self._finalizeExpand(content, divider, parentStatus, replies.length);
                    }).catch(function(err) {
                        self._view.showError(err.message);
                    });
                }
            } else {
                self._finalizeExpand(content, divider, parentStatus, repliesContainer.children.length);
            }
        }
    }

    _finalizeExpand(content, divider, parentStatus, count) {
        var label = divider.querySelector(".response-divider-label");
        if (label) label.textContent = '💬 ' + count + ' Response' + (count !== 1 ? 's' : '') + '  ▾';

        // Wait for images inside the content to load before measuring height
        var images = content.querySelectorAll("img");
        var pending = images.length;
        var setHeight = function() {
            content.style.maxHeight = content.scrollHeight + "px";
            content.style.opacity = "1";
        };

        if (pending === 0) {
            setHeight();
        } else {
            var done = 0;
            for (var i = 0; i < images.length; i++) {
                var img = images[i];
                if (img.complete) {
                    done++;
                    if (done === pending) setHeight();
                } else {
                    img.addEventListener("load", function() {
                        done++;
                        if (done === pending) setHeight();
                    }, { once: true });
                    img.addEventListener("error", function() {
                        done++;
                        if (done === pending) setHeight();
                    }, { once: true });
                }
            }
            // Fallback: set height after 1s even if images haven't all loaded
            if (done < pending) {
                setTimeout(function() {
                    if (content.style.opacity === "0" || content.style.maxHeight === "0px") {
                        setHeight();
                    }
                }, 1000);
            }
        }
    }

    _renderReplies(replies, container, parentId) {
        var self = this;
        for (var i = 0; i < replies.length; i++) {
            var reply = replies[i];
            var replyToName = reply.replyTo && reply.replyTo.user ? reply.replyTo.user.name : "";
            var canEdit = api.isLoggedIn() && api.userName && api.userName.toLowerCase() === (reply.user && reply.user.name ? reply.user.name.toLowerCase() : "");

            var _replyId = reply.id;
            var _replyText = reply.text || "";

            var replyView = new StatusMiniView(reply, {
                isReply: true,
                nestLevel: 1,
                replyToName: replyToName,
                canEditStatus: canEdit ? function() { return true; } : null,
                canDeleteStatus: canEdit ? function() { return true; } : null,
                onReply: function(s) { router.show(uri.formatClientLink("status", s.id)); },
                onFavorite: function(s) {
                    var p = s.ownFavorite ? s.unfavorite() : s.favorite();
                    p.catch(function(err) { self._view.showError(err.message); });
                },
                onRepost: function(s) {
                    s.undoRepost().then(function() {
                        self._view.showSuccess("Repost removed.");
                        self._loadTimeline();
                    }).catch(function(err) { self._view.showError(err.message); });
                },
                onRepostWithText: function(s, text) {
                    s.repost(text).then(function() {
                        self._view.showSuccess("Reposted!");
                        self._loadTimeline();
                    }).catch(function(err) { self._view.showError(err.message); });
                },
                // onEdit handled by StatusMiniView._startEdit() → dispatches "edit" event
                // onDelete MUST NOT be set — we use event listener below exclusively
            });
            container.appendChild(replyView.hostNode);

            // Wire delete event — use event dispatch only, show ID for safety
            replyView.addEventListener("delete", function(e) {
                var toDelete = e.detail.status;
                if (toDelete.id !== _replyId) {
                    self._view.showError("Delete mismatch: expected reply #" + _replyId + " but got #" + toDelete.id);
                    return;
                }
                var preview = _replyText.length > 40 ? _replyText.substring(0, 40) + "..." : _replyText;
                if (confirm("Delete your reply?\n\n\"" + preview + "\"\n\n(ID: " + _replyId + ")")) {
                    toDelete.delete().then(function() {
                        if (parentId && self._repliesCache[parentId]) {
                            self._repliesCache[parentId] = self._repliesCache[parentId].filter(function(r) { return r.id !== _replyId; });
                            container.innerHTML = "";
                            self._renderReplies(self._repliesCache[parentId], container, parentId);
                        }
                        self._view.showSuccess("Deleted!");
                    }).catch(function(err) {
                        self._view.showError(err.message);
                    });
                }
            });

            // Wire edit event — update reply in cache, re-render
            replyView.addEventListener("edit", function(e) {
                var edited = e.detail.status;
                if (parentId && self._repliesCache[parentId]) {
                    var cache = self._repliesCache[parentId];
                    for (var j = 0; j < cache.length; j++) {
                        if (cache[j].id === edited.id) {
                            cache[j] = edited;
                            break;
                        }
                    }
                    container.innerHTML = "";
                    self._renderReplies(cache, container, parentId);
                } else {
                    self._view.showSuccess("Updated!");
                    self._loadTimeline();
                }
            });
        }
    }

    _handleThreadCompose(parentStatus, input, sendBtn, section, divider, content, repliesContainer, composer) {
        var self = this;
        var text = input.value.trim();
        if (!text) return;

        sendBtn.disabled = true;
        input.disabled = true;

        Status.create(text, null, parentStatus.id)
            .then(function(newStatus) {
                input.value = "";
                input.style.height = "auto";
                sendBtn.disabled = false;
                input.disabled = false;

                // Add to cache and re-render
                if (!self._repliesCache[parentStatus.id]) {
                    self._repliesCache[parentStatus.id] = [];
                }
                self._repliesCache[parentStatus.id].push(newStatus);

                // Re-render replies
                repliesContainer.innerHTML = "";
                self._renderReplies(self._repliesCache[parentStatus.id], repliesContainer, parentStatus.id);

                // Update expanded state
                self._finalizeExpand(content, divider, parentStatus, self._repliesCache[parentStatus.id].length);

                self._view.showSuccess("Reply posted!");
            })
            .catch(function(err) {
                sendBtn.disabled = false;
                input.disabled = false;
                self._view.showError(err.message);
            });
    }

    _wireMiniView(miniView) {
        var self = this;
        miniView.addEventListener("reply", function(e) {
            router.show(uri.formatClientLink("status", e.detail.status.id));
        });
        miniView.addEventListener("favorite", function(e) {
            var s = e.detail.status;
            var p = s.ownFavorite ? s.unfavorite() : s.favorite();
            p.catch(function(err) { self._view.showError(err.message); });
        });
        miniView.addEventListener("repost", function(e) {
            // Handled by StatusMiniView._showRepostComposer() via options callback
        });
        miniView.addEventListener("edit", function(e) {
            self._view.showSuccess("Updated!");
            // StatusMiniView already re-renders itself via _startEdit → no reload needed
        });
        miniView.addEventListener("delete", function(e) {
            if (confirm("Delete?")) {
                e.detail.status.delete()
                    .then(function() {
                        // Remove card from DOM without full reload
                        var host = miniView.hostNode;
                        if (host && host.parentNode) host.parentNode.removeChild(host);
                        self._view.showSuccess("Deleted!");
                    })
                    .catch(function(err) { self._view.showError(err.message); });
            }
        });
    }
}

module.exports = function(router) {
    router.enter(["timeline"], function(ctx, next) {
        ctx.controller = new StatusController(ctx);
    });
};
