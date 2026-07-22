"use strict";

const events = require("../events.js");
const views = require("../util/views.js");
const PostList = require("../models/post_list.js");
const api = require("../api.js");
const uri = require("../util/uri.js");

const pageTemplate = views.getTemplate("community");

class CommunityView extends events.EventTarget {
    constructor(ctx) {
        super();
        this._ctx = ctx;
        this._hostNode = document.getElementById("content-holder");
        this._currentQuery = "";
        views.replaceContent(this._hostNode, pageTemplate(ctx));

        this._bindTabs();
        this._bindSort();
    }

    _bindTabs() {
        for (let tabNode of this._hostNode.querySelectorAll(".feed-tab")) {
            tabNode.addEventListener("click", (e) => {
                e.preventDefault();
                const feed = tabNode.getAttribute("data-feed");
                this._ctx.parameters.feed = feed;
                this._ctx.parameters.offset = 0;
                this.dispatchEvent(
                    new CustomEvent("navigate", {
                        detail: { parameters: Object.assign({}, this._ctx.parameters) },
                    })
                );
            });
        }
    }

    _bindSort() {
        for (let btn of this._hostNode.querySelectorAll(".sort-btn")) {
            btn.addEventListener("click", (e) => {
                e.preventDefault();
                const sort = btn.getAttribute("data-sort") || null;
                this._ctx.parameters.sort = sort;
                this._ctx.parameters.offset = 0;
                this.dispatchEvent(
                    new CustomEvent("navigate", {
                        detail: { parameters: Object.assign({}, this._ctx.parameters) },
                    })
                );
            });
        }
    }

    loadPosts(query, offset, limit) {
        this._currentQuery = query;
        const fields = [
            "id", "thumbnailUrl", "type", "safety",
            "score", "favoriteCount", "commentCount", "tags", "version",
        ];
        return PostList.search(query, offset, limit, fields).then((response) => {
            const grid = this._hostNode.querySelector(".community-post-grid");
            if (!grid) return response;

            if (!response.results || response.results.length === 0) {
                grid.innerHTML = '<p class="empty-feed">No posts to show. Follow users or upload content to see something here.</p>';
            } else {
                try {
                    var html = '<ul class="post-thumbnail-list">';
                    response.results.map(function(post) {
                        var url = uri.formatClientLink("post", post.id);
                        var thumb = views.makeThumbnail(post.thumbnailUrl);
                        var tags = (post.tags && post.tags.map) ? post.tags.map(function(t) { return t.names[0]; }).join(' ') : '';
                        html += '<li data-post-id="' + post.id + '">';
                        html += '<a class="thumbnail-wrapper" title="' + tags + '" href="' + url + '">';
                        html += thumb;
                        html += '</a></li>';
                    });
                    html += '</ul>';
                    grid.innerHTML = html;
                } catch (e) {
                    grid.innerHTML = '<p class="empty-feed">Error: ' + e.message + '</p>';
                }
            }
            return response;
        }).catch(function(err) {
            var grid = this._hostNode.querySelector(".community-post-grid");
            if (grid) grid.innerHTML = '<p class="empty-feed">Error loading: ' + err.message + '</p>';
        }.bind(this));
    }

    setComposer(composerNode) {
        const container = this._hostNode.querySelector(".status-composer-container");
        if (container && composerNode) {
            container.innerHTML = "";
            if (composerNode.hostNode) {
                container.appendChild(composerNode.hostNode);
            } else if (composerNode instanceof Node) {
                container.appendChild(composerNode);
            }
        }
    }

    showSuccess(message) {
        views.showSuccess(this._hostNode, message);
    }

    showError(message) {
        views.showError(this._hostNode, message);
    }

    clearMessages() {
        views.clearMessages(this._hostNode);
    }
}

module.exports = CommunityView;
