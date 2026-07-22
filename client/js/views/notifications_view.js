"use strict";

const views = require("../util/views.js");
const notifications = require("../models/notifications.js");

const template = views.getTemplate("notifications");

class NotificationsView {
    constructor() {
        this._hostNode = document.getElementById("content-holder");
        this._installEventHandlers();
    }

    _installEventHandlers() {
        notifications.addEventListener("change", (e) =>
            this._evtChange(e)
        );
    }

    _evtChange(e) {
        this.render();
    }

    _formatTime(timeStr) {
        if (!timeStr) return "";
        const date = new Date(timeStr);
        const now = new Date();
        const diff = now - date;
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);

        if (minutes < 1) return "just now";
        if (minutes < 60) return minutes + "m ago";
        if (hours < 24) return hours + "h ago";
        if (days < 7) return days + "d ago";
        return date.toLocaleDateString();
    }

    render() {
        const ctx = {
            notifications: notifications.results,
            getIcon: (type) => notifications.getTypeIcon(type),
            getLabel: (type) => notifications.getTypeLabel(type),
            formatTime: (time) => this._formatTime(time),
        };

        views.replaceContent(this._hostNode, template(ctx));
        this._bindActions();
    }

    _bindActions() {
        const host = this._hostNode;

        // Mark single as read
        for (let btn of host.querySelectorAll(".mark-read")) {
            btn.addEventListener("click", (e) => {
                e.preventDefault();
                const item = btn.closest(".notification-item");
                const id = parseInt(item.dataset.id);
                notifications.markRead(id).then(() => {
                    item.classList.add("unread");
                });
            });
        }

        // Dismiss single
        for (let btn of host.querySelectorAll(".dismiss")) {
            btn.addEventListener("click", (e) => {
                e.preventDefault();
                const item = btn.closest(".notification-item");
                const id = parseInt(item.dataset.id);
                notifications.dismiss(id).then(() => {
                    item.remove();
                    if (
                        !host.querySelectorAll(".notification-item").length
                    ) {
                        this.render();
                    }
                });
            });
        }

        // Mark all read
        const markAllBtn = host.querySelector(".mark-all-read");
        if (markAllBtn) {
            markAllBtn.addEventListener("click", (e) => {
                e.preventDefault();
                notifications.markAllRead().then(() => this.render());
            });
        }

        // Dismiss all
        const dismissAllBtn = host.querySelector(".dismiss-all");
        if (dismissAllBtn) {
            dismissAllBtn.addEventListener("click", (e) => {
                e.preventDefault();
                notifications.dismissAll().then(() => this.render());
            });
        }

        // Click notification to navigate
        for (let item of host.querySelectorAll(".notification-item")) {
            item.addEventListener("click", function (e) {
                if (
                    e.target.closest("button") ||
                    e.target.closest("a")
                ) {
                    return;
                }
                const id = parseInt(this.dataset.id);
                notifications.markRead(id);
                const notif = notifications.results.find(
                    (n) => n.id === id
                );
                if (notif) {
                    const link = notifications.getLink(notif);
                    if (link) {
                        const router = require("../router.js");
                        router.show(link);
                    }
                }
            });
        }
    }
}

module.exports = NotificationsView;
