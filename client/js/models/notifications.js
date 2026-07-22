"use strict";

const events = require("../events.js");
const api = require("../api.js");
const uri = require("../util/uri.js");

class NotificationList extends events.EventTarget {
    constructor() {
        super();
        this._results = [];
        this._unreadCount = 0;
    }

    get results() {
        return this._results;
    }

    get unreadCount() {
        return this._unreadCount;
    }

    fetch(offset, limit) {
        return api
            .get(
                uri.formatApiLink("notifications", {
                    offset: offset || 0,
                    limit: limit || 50,
                })
            )
            .then(
                (response) => {
                    this._results = response.results;
                    this.dispatchEvent(
                        new CustomEvent("change", {
                            detail: { results: this._results },
                        })
                    );
                    return Promise.resolve(this._results);
                },
                (error) => {
                    this.dispatchEvent(new CustomEvent("error"));
                    return Promise.reject(error);
                }
            );
    }

    fetchUnreadCount() {
        return api
            .get(uri.formatApiLink("notifications/unread-count"))
            .then(
                (response) => {
                    this._unreadCount = response.count;
                    this.dispatchEvent(
                        new CustomEvent("unreadChange", {
                            detail: { count: this._unreadCount },
                        })
                    );
                    return Promise.resolve(this._unreadCount);
                },
                (error) => {
                    return Promise.reject(error);
                }
            );
    }

    markRead(notificationId) {
        return api
            .post(uri.formatApiLink("notification", notificationId, "read"))
            .then(() => {
                this._unreadCount = Math.max(0, this._unreadCount - 1);
                this.fetchUnreadCount();
            });
    }

    markAllRead() {
        return api
            .post(uri.formatApiLink("notifications/read-all"))
            .then(() => {
                this._unreadCount = 0;
                this.dispatchEvent(
                    new CustomEvent("unreadChange", {
                        detail: { count: 0 },
                    })
                );
            });
    }

    dismiss(notificationId) {
        return api
            .delete(uri.formatApiLink("notification", notificationId))
            .then(() => {
                this._unreadCount = Math.max(0, this._unreadCount - 1);
                this.fetchUnreadCount();
            });
    }

    dismissAll() {
        return api
            .delete(uri.formatApiLink("notifications", "dismiss-all"))
            .then(() => {
                this._unreadCount = 0;
                this._results = [];
                this.dispatchEvent(
                    new CustomEvent("change", {
                        detail: { results: [] },
                    })
                );
            });
    }

    getTypeLabel(type) {
        const labels = {
            post_like: "liked your post",
            post_dislike: "disliked your post",
            post_favorite: "favorited your post",
            post_comment: "commented on your post",
            status_favorite: "favorited your status",
            status_reply: "replied to your status",
            new_post: "posted",
            new_status: "posted a status",
            new_message: "sent you a message",
        };
        return labels[type] || type;
    }

    getTypeIcon(type) {
        const icons = {
            post_like: "fa-heart",
            post_dislike: "fa-thumbs-down",
            post_favorite: "fa-star",
            post_comment: "fa-comment",
            status_favorite: "fa-heart",
            status_reply: "fa-reply",
            new_post: "fa-image",
            new_status: "fa-pencil",
            new_message: "fa-envelope",
        };
        return icons[type] || "fa-bell";
    }

    getLink(notification) {
        if (notification.post && notification.post.id) {
            return "/post/" + notification.post.id;
        }
        if (notification.status && notification.status.id) {
            return "/status/" + notification.status.id;
        }
        return null;
    }
}

module.exports = new NotificationList();
