"use strict";

const api = require("../api.js");
const topNavigation = require("../models/top_navigation.js");
const notifications = require("../models/notifications.js");
const TopNavigationView = require("../views/top_navigation_view.js");

class TopNavigationController {
    constructor() {
        api.fetchConfig().then(() => {
            this._topNavigationView = new TopNavigationView();

            topNavigation.addEventListener("activate", (e) =>
                this._evtActivate(e)
            );

            api.addEventListener("login", (e) => {
                this._evtAuthChange(e);
                this._pollNotifications();
            });
            api.addEventListener("logout", (e) => this._evtAuthChange(e));

            notifications.addEventListener("unreadChange", (e) =>
                this._evtUnreadChange(e)
            );

            this._render();
            this._pollNotifications();
            // Poll every 10 minutes
            setInterval(() => this._pollNotifications(), 600000);
        });
    }

    _pollNotifications() {
        if (api.isLoggedIn()) {
            notifications.fetchUnreadCount().catch(() => {});
        }
    }

    _evtUnreadChange(e) {
        this._render();
    }

    _evtAuthChange(e) {
        this._render();
    }

    _evtActivate(e) {
        this._topNavigationView.activate(e.detail.key);
    }

    _updateNavigationFromPrivileges() {
        topNavigation.get("account").url = "user/" + api.userName;
        topNavigation.get("account").imageUrl = api.user
            ? api.user.avatarUrl
            : null;

        topNavigation.showAll();
        // Notifications is now a standalone bell, not a menu item
        topNavigation.hide("notifications");
        if (!api.hasPrivilege("posts:list")) {
            topNavigation.hide("posts");
        }
        if (!api.hasPrivilege("posts:create")) {
            topNavigation.hide("upload");
        }
        // Comments always hidden from main menu
        topNavigation.hide("comments");
        if (!api.hasPrivilege("tags:list")) {
            topNavigation.hide("tags");
        }
        if (!api.hasPrivilege("users:list")) {
            topNavigation.hide("users");
        }
        if (!api.hasPrivilege("pools:list")) {
            topNavigation.hide("pools");
        }
        if (api.isLoggedIn()) {
            topNavigation.hide("register");
            topNavigation.hide("login");
        } else {
            if (!api.hasPrivilege("users:create:self")) {
                topNavigation.hide("register");
            }
            topNavigation.hide("account");
            topNavigation.hide("logout");
        }
    }

    _render() {
        this._updateNavigationFromPrivileges();
        this._topNavigationView.render({
            items: topNavigation.getAll(),
            name: api.getName(),
            unreadCount: api.isLoggedIn() ? notifications.unreadCount : 0,
        });
        this._topNavigationView.activate(
            topNavigation.activeItem ? topNavigation.activeItem.key : ""
        );
    }
}

module.exports = new TopNavigationController();
