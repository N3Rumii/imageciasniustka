"use strict";

const router = require("../router.js");
const api = require("../api.js");
const topNavigation = require("../models/top_navigation.js");
const notifications = require("../models/notifications.js");
const NotificationsView = require("../views/notifications_view.js");

class NotificationsController {
    constructor(ctx) {
        topNavigation.activate("notifications");
        topNavigation.setTitle("Notifications");

        this._ctx = ctx;
        this._view = null;
        this._pollInterval = null;

        this._init();
    }

    _init() {
        this._view = new NotificationsView();

        notifications.fetch(0, 50).then(
            () => {
                this._view.render();
            },
            (error) => {
                if (this._ctx.controller && this._ctx.controller.showError) {
                    this._ctx.controller.showError(
                        "Could not fetch notifications: " + error.message
                    );
                }
            }
        );

        // Start polling for unread count
        this._startPolling();
    }

    _startPolling() {
        if (this._pollInterval) return;
        notifications.fetchUnreadCount();
        this._pollInterval = setInterval(() => {
            if (api.isLoggedIn()) {
                notifications.fetchUnreadCount();
            }
        }, 60000);
    }
}

module.exports = function (router) {
    router.enter(["notifications"], function (ctx, next) {
        ctx.controller = new NotificationsController(ctx);
    });
};
