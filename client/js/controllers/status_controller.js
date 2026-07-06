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
        this._loadTimeline();
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
                self._loadTimeline();
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
                self._loadTimeline();
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

    _loadTimeline() {
        var self = this;
        var params = this._buildParams();

        Status.getTimeline(params)
            .then(function(statuses) {
                self._renderStatuses(statuses);
            })
            .catch(function(err) {
                self._view.showError(err.message);
            });
    }

    _renderStatuses(statuses) {
        this._statusViews = [];
        this._listNode.innerHTML = "";

        if (!statuses || statuses.length === 0) {
            this._listNode.innerHTML = '<div class="status-empty"><p>No statuses yet. Be the first!</p></div>';
            return;
        }

        var self = this;
        for (var i = 0; i < statuses.length; i++) {
            var status = statuses[i];
            var canEdit = api.isLoggedIn() && api.userName && api.userName.toLowerCase() === (status.user && status.user.name ? status.user.name.toLowerCase() : "");
            var miniView = new StatusMiniView(status, {
                canEditStatus: canEdit ? function() { return true; } : null,
                canDeleteStatus: canEdit ? function() { return true; } : null,
                onReply: function(s) {
                    router.show(uri.formatClientLink("status", s.id));
                },
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
                    var t = prompt("Edit:", s.text || "");
                    if (t !== null && t !== s.text) {
                        s.text = t;
                        s.save()
                            .then(function() { self._view.showSuccess("Updated!"); self._loadTimeline(); })
                            .catch(function(err) { self._view.showError(err.message); });
                    }
                },
                onDelete: function(s) {
                    if (confirm("Delete?")) {
                        s.delete()
                            .then(function() { self._view.showSuccess("Deleted!"); self._loadTimeline(); })
                            .catch(function(err) { self._view.showError(err.message); });
                    }
                },
            });
            this._statusViews.push(miniView);
            this._listNode.appendChild(miniView._hostNode);
        }
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
            self._loadTimeline();
        });
        miniView.addEventListener("delete", function(e) {
            if (confirm("Delete?")) {
                e.detail.status.delete()
                    .then(function() { self._view.showSuccess("Deleted!"); self._loadTimeline(); })
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
