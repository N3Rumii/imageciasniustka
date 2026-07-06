"use strict";

const events = require("../events.js");
const views = require("../util/views.js");
const Status = require("../models/status.js");

const template = views.getTemplate("status-mini");

class StatusMiniView extends events.EventTarget {
    constructor(status, options) {
        super();
        options = options || {};
        this._options = options;
        this._status = status;
        this._hostNode = options.hostNode || document.createElement("div");
        this._hostNode.innerHTML = "";

        const ctx = {
            status: status,
            formatClientLink: function(type, id) {
                const uri = require("../util/uri.js");
                if (type === "status") {
                    return uri.formatClientLink("status", id);
                }
                return uri.formatClientLink(type, id);
            },
            makeRelativeTime: function(time) {
                if (!time) return "";
                var diff = Date.now() - new Date(time).getTime();
                var seconds = Math.floor(diff / 1000);
                if (seconds < 60) return "just now";
                if (seconds < 3600) return Math.floor(seconds / 60) + "m";
                if (seconds < 86400) return Math.floor(seconds / 3600) + "h";
                if (seconds < 604800) return Math.floor(seconds / 86400) + "d";
                return new Date(time).toLocaleDateString();
            },
            makeMarkdown: function(text) {
                if (!text) return "";
                var escaped = text
                    .replace(/&/g, "&amp;")
                    .replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;");
                escaped = escaped.replace(
                    /#([a-zA-Z0-9_]+)/g,
                    '<a href="/timeline?tag=$1">#$1</a>'
                );
                escaped = escaped.replace(/\n/g, "<br>");
                return escaped;
            },
            encodeURIComponent: encodeURIComponent,
            canEditStatus: options.canEditStatus || null,
            canDeleteStatus: options.canDeleteStatus || null,
        };

        var rendered = template(ctx);
        views.replaceContent(this._hostNode, rendered);

        this._status.addEventListener("change", function() {
            this._hostNode.innerHTML = "";
            views.replaceContent(this._hostNode, template(ctx));
            this._bindEvents();
        }.bind(this));

        this._bindEvents();
    }

    _bindEvents() {
        var self = this;
        var actions = this._hostNode.querySelectorAll(".status-mini-action");
        for (let i = 0; i < actions.length; i++) {
            let btn = actions[i];
            let action = btn.getAttribute("data-action");
            if (!action) continue;
            btn.addEventListener("click", function(e) {
                e.preventDefault();
                e.stopPropagation();
                switch (action) {
                    case "reply":
                        if (self._options.onReply) self._options.onReply(self._status);
                        break;
                    case "favorite":
                        if (self._options.onFavorite) self._options.onFavorite(self._status);
                        break;
                    case "repost":
                        if (self._status.ownRepost) {
                            // Already reposted — undo
                            if (self._options.onRepost) self._options.onRepost(self._status);
                        } else {
                            // Show inline composer
                            self._showRepostComposer();
                        }
                        break;
                    case "toggle-actions":
                        var menu = this.closest(".status-mini-menu");
                        if (menu) {
                            menu.classList.toggle("open");
                        }
                        break;
                    case "edit":
                        self._startEdit();
                        var menu2 = this.closest(".status-mini-menu");
                        if (menu2) menu2.classList.remove("open");
                        break;
                    case "delete":
                        if (self._options.onDelete) self._options.onDelete(self._status);
                        var menu3 = this.closest(".status-mini-menu");
                        if (menu3) menu3.classList.remove("open");
                        break;
                }
            });
        }
        // Close dropdown when clicking outside
        document.addEventListener("click", function(e) {
            var menus = self._hostNode.querySelectorAll(".status-mini-menu.open");
            for (var m = 0; m < menus.length; m++) {
                if (!menus[m].contains(e.target)) {
                    menus[m].classList.remove("open");
                }
            }
        });
    }

    _showRepostComposer() {
        var self = this;
        var composer = this._hostNode.querySelector(".status-mini-repost-composer");
        if (!composer) return;
        composer.style.display = "block";
        var textarea = composer.querySelector(".status-mini-repost-input");
        var submitBtn = composer.querySelector(".status-mini-repost-submit");
        var cancelBtn = composer.querySelector(".status-mini-repost-cancel");

        textarea.focus();

        submitBtn.onclick = function() {
            var msg = textarea.value.trim();
            composer.style.display = "none";
            textarea.value = "";
            if (self._options.onRepostWithText) {
                self._options.onRepostWithText(self._status, msg || null);
            } else if (self._options.onRepost) {
                self._options.onRepost(self._status);
            }
        };

        cancelBtn.onclick = function() {
            composer.style.display = "none";
            textarea.value = "";
        };

        // Ctrl+Enter to submit
        textarea.onkeydown = function(e) {
            if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                submitBtn.click();
            }
        };
    }

    _startEdit() {
        var self = this;
        var textEl = this._hostNode.querySelector(".status-mini-text");
        if (!textEl) {
            // No text element, create one
            var bodyEl = this._hostNode.querySelector(".status-mini-body");
            if (!bodyEl) return;
            textEl = document.createElement("div");
            textEl.className = "status-mini-text";
            // Insert after header or at top
            var header = bodyEl.querySelector(".status-mini-header");
            if (header && header.nextSibling) {
                bodyEl.insertBefore(textEl, header.nextSibling);
            } else if (header) {
                header.parentNode.insertBefore(textEl, header.nextSibling);
            } else {
                bodyEl.insertBefore(textEl, bodyEl.firstChild);
            }
        }

        var originalHTML = textEl.innerHTML;
        var originalText = self._status.text || "";

        // Replace with textarea and buttons
        var editHTML = '<div class="status-mini-edit-area">';
        editHTML += '<textarea class="status-mini-edit-input">' + originalText + '</textarea>';
        editHTML += '<div class="status-mini-edit-buttons">';
        editHTML += '<button class="status-mini-edit-save">Save</button>';
        editHTML += '<button class="status-mini-edit-cancel">Cancel</button>';
        editHTML += '</div></div>';

        textEl.innerHTML = editHTML;

        var textarea = textEl.querySelector(".status-mini-edit-input");
        var saveBtn = textEl.querySelector(".status-mini-edit-save");
        var cancelBtn = textEl.querySelector(".status-mini-edit-cancel");

        textarea.focus();
        textarea.setSelectionRange(textarea.value.length, textarea.value.length);

        saveBtn.addEventListener("click", function() {
            var newText = textarea.value.trim();
            if (newText !== self._status.text) {
                self._status.text = newText;
                self._status.save().then(function() {
                    self.dispatchEvent(
                        new CustomEvent("edit", {
                            detail: { status: self._status },
                        })
                    );
                }).catch(function(err) {
                    textEl.innerHTML = originalHTML;
                    self._bindEvents();
                });
            } else {
                textEl.innerHTML = originalHTML;
                self._bindEvents();
            }
        });

        cancelBtn.addEventListener("click", function() {
            textEl.innerHTML = originalHTML;
            self._bindEvents();
        });

        // Ctrl+Enter to save
        textarea.addEventListener("keydown", function(e) {
            if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                saveBtn.click();
            }
        });
    }

    get hostNode() {
        return this._hostNode;
    }
}

module.exports = StatusMiniView;
