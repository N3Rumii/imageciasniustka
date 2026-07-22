"use strict";

const events = require("../events.js");
const views = require("../util/views.js");
const StatusMiniView = require("./status_mini_view.js");
const StatusComposerView = require("./status_composer_view.js");

const template = views.getTemplate("status-detail");

class StatusDetailView extends events.EventTarget {
    constructor(status, replies) {
        super();
        this._status = status;
        this._replies = replies || [];
        this._hostNode = document.getElementById("content-holder");
        this._render();
    }

    _render() {
        const ctx = {
            status: this._status,
            replies: this._replies,
            formatClientLink: (type, id) => {
                const uri = require("../util/uri.js");
                return uri.formatClientLink(type, id);
            },
            canEditStatus: (status) => {
                const api = require("../api.js");
                return status.user && api.userName &&
                    api.userName.toLowerCase() === status.user.name.toLowerCase();
            },
            canDeleteStatus: (status) => {
                const api = require("../api.js");
                return status.user && api.userName &&
                    api.userName.toLowerCase() === status.user.name.toLowerCase();
            },
            renderStatusMini: (status) => {
                const api = require("../api.js");
                const view = new StatusMiniView(status, {
                    canEditStatus: status.user && api.userName &&
                        api.userName.toLowerCase() === status.user.name.toLowerCase()
                            ? () => true : null,
                    canDeleteStatus: status.user && api.userName &&
                        api.userName.toLowerCase() === status.user.name.toLowerCase()
                            ? () => true : null,
                });
                return view.hostNode.outerHTML || view.hostNode.innerHTML;
            },
        };
        views.replaceContent(this._hostNode, template(ctx));

        // Wire up the main status
        this._wireMainStatus();
        // Wire up replies
        this._wireReplies();
        // Add composer for replying
        this._addComposer();
    }

    _wireMainStatus() {
        const mainNode = this._hostNode.querySelector(".status-detail-main");
        if (!mainNode) return;

        const actionBtns = mainNode.querySelectorAll(".status-mini-action");
        for (let btn of actionBtns) {
            const action = btn.getAttribute("data-action");
            if (!action) continue;
            btn.addEventListener("click", (e) => {
                if (action === "toggle-actions") {
                    const menu = btn.closest(".status-mini-menu");
                    if (menu) {
                        menu.classList.toggle("open");
                    }
                    return;
                }
                e.preventDefault();
                this._handleAction(action);
            });
        }
    }

    _wireReplies() {
        const repliesNode = this._hostNode.querySelector(".status-detail-replies");
        if (!repliesNode) return;

        const replyCards = repliesNode.querySelectorAll(".status-mini");
        for (let k = 0; k < replyCards.length; k++) {
            const card = replyCards[k];
            const replyStatus = this._replies[k];  // match card to its Status object
            if (!replyStatus) continue;

            const actionBtns = card.querySelectorAll(".status-mini-action");
            for (let btn of actionBtns) {
                const action = btn.getAttribute("data-action");
                if (!action) continue;
                btn.addEventListener("click", (e) => {
                    if (action === "toggle-actions") {
                        const menu = btn.closest(".status-mini-menu");
                        if (menu) {
                            menu.classList.toggle("open");
                        }
                        return;
                    }
                    e.preventDefault();
                    this._handleReplyAction(action, replyStatus, card);
                });
            }
        }
    }

    _startEditMain() {
        const mainNode = this._hostNode.querySelector(".status-detail-main");
        if (!mainNode) return;
        const textEl = mainNode.querySelector(".status-mini-text");
        if (!textEl) return;

        const originalHTML = textEl.innerHTML;
        const originalText = this._status.text || "";

        textEl.innerHTML =
            '<div class="status-mini-edit-area">' +
            '<textarea class="status-mini-edit-input">' +
            this._escapeHtml(originalText) +
            "</textarea>" +
            '<div class="status-mini-edit-buttons">' +
            '<button class="status-mini-edit-save">Save</button>' +
            '<button class="status-mini-edit-cancel">Cancel</button>' +
            "</div></div>";

        const textarea = textEl.querySelector(".status-mini-edit-input");
        const saveBtn = textEl.querySelector(".status-mini-edit-save");
        const cancelBtn = textEl.querySelector(".status-mini-edit-cancel");

        textarea.focus();
        textarea.setSelectionRange(textarea.value.length, textarea.value.length);

        const restore = () => {
            textEl.innerHTML = originalHTML;
            this._wireMainStatus();
        };

        saveBtn.addEventListener("click", () => {
            const newText = textarea.value.trim();
            if (newText !== originalText) {
                this._status.text = newText;
                this._status
                    .save()
                    .then(() => {
                        this.dispatchEvent(
                            new CustomEvent("edit", {
                                detail: { status: this._status },
                            })
                        );
                        restore();
                        this._render();
                    })
                    .catch((err) => {
                        restore();
                    });
            } else {
                restore();
            }
        });

        cancelBtn.addEventListener("click", restore);

        textarea.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                saveBtn.click();
            }
        });
    }

    _escapeHtml(text) {
        if (!text) return "";
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&apos;");
    }

    _addComposer() {
        const container = this._hostNode.querySelector(".status-composer-container");
        if (!container) return;

        this._composerView = new StatusComposerView({
            hostNode: container,
            parentStatus: this._status,
        });
        this._composerView.addEventListener("submit", (e) => {
            this.dispatchEvent(
                new CustomEvent("submitReply", {
                    detail: {
                        text: e.detail.text,
                        file: e.detail.file,
                        parentId: this._status.id,
                    },
                })
            );
        });
    }

    _handleAction(action) {
        switch (action) {
            case "reply":
                this.dispatchEvent(
                    new CustomEvent("reply", { detail: { status: this._status } })
                );
                break;
            case "favorite":
                this.dispatchEvent(
                    new CustomEvent("favorite", { detail: { status: this._status } })
                );
                break;
            case "repost":
                this.dispatchEvent(
                    new CustomEvent("repost", { detail: { status: this._status } })
                );
                break;
            case "edit":
                this._startEditMain();
                break;
            case "delete":
                this.dispatchEvent(
                    new CustomEvent("delete", { detail: { status: this._status } })
                );
                break;
        }
    }

    _handleReplyAction(action, replyStatus, card) {
        switch (action) {
            case "reply":
                this.dispatchEvent(
                    new CustomEvent("reply", { detail: { status: replyStatus } })
                );
                break;
            case "favorite":
                this.dispatchEvent(
                    new CustomEvent("favorite", { detail: { status: replyStatus } })
                );
                break;
            case "repost":
                this.dispatchEvent(
                    new CustomEvent("repost", { detail: { status: replyStatus } })
                );
                break;
            case "edit":
                this._startEditReply(replyStatus, card);
                break;
            case "delete":
                this.dispatchEvent(
                    new CustomEvent("delete", { detail: { status: replyStatus } })
                );
                break;
        }
    }

    _startEditReply(replyStatus, card) {
        const textEl = card.querySelector(".status-mini-text");
        if (!textEl) return;

        const originalHTML = textEl.innerHTML;
        const originalText = replyStatus.text || "";

        textEl.innerHTML =
            '<div class="status-mini-edit-area">' +
            '<textarea class="status-mini-edit-input">' +
            this._escapeHtml(originalText) +
            "</textarea>" +
            '<div class="status-mini-edit-buttons">' +
            '<button class="status-mini-edit-save">Save</button>' +
            '<button class="status-mini-edit-cancel">Cancel</button>' +
            "</div></div>";

        const textarea = textEl.querySelector(".status-mini-edit-input");
        const saveBtn = textEl.querySelector(".status-mini-edit-save");
        const cancelBtn = textEl.querySelector(".status-mini-edit-cancel");

        textarea.focus();
        textarea.setSelectionRange(textarea.value.length, textarea.value.length);

        const restore = () => {
            textEl.innerHTML = originalHTML;
        };

        saveBtn.addEventListener("click", () => {
            const newText = textarea.value.trim();
            if (newText !== originalText) {
                replyStatus.text = newText;
                replyStatus.save()
                    .then(() => {
                        this.dispatchEvent(
                            new CustomEvent("edit", {
                                detail: { status: replyStatus },
                            })
                        );
                        restore();
                        this._render();
                    })
                    .catch(() => restore());
            } else {
                restore();
            }
        });

        cancelBtn.addEventListener("click", restore);

        textarea.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                saveBtn.click();
            }
        });
    }

    addReply(status) {
        this._replies.push(status);
        this._render();
    }

    showSuccess(message) {
        views.showSuccess(this._hostNode, message);
    }

    showError(message) {
        views.showError(this._hostNode, message);
    }
}

module.exports = StatusDetailView;
