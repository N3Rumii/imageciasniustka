"use strict";

const router = require("../router.js");
const api = require("../api.js");
const uri = require("../util/uri.js");
const topNavigation = require("../models/top_navigation.js");
const Status = require("../models/status.js");
const StatusDetailView = require("../views/status_detail_view.js");
const EmptyView = require("../views/empty_view.js");

class StatusDetailController {
    constructor(ctx) {
        if (!api.hasPrivilege("statuses:view")) {
            this._view = new EmptyView();
            this._view.showError("You don't have privileges to view statuses.");
            return;
        }

        topNavigation.activate("community");
        topNavigation.setTitle("Status");

        this._ctx = ctx;
        this._statusId = parseInt(ctx.parameters.id, 10);

        this._load();
    }

    _load() {
        Status.get(this._statusId)
            .then((status) => {
                return status.getReplies().then((replies) => {
                    this._status = status;
                    this._view = new StatusDetailView(status, replies);
                    this._setupEvents();
                });
            })
            .catch((error) => {
                if (!this._view) {
                    this._view = new EmptyView();
                }
                this._view.showError(error.message);
            });
    }

    _setupEvents() {
        this._view.addEventListener("favorite", (e) => {
            const status = e.detail.status;
            const promise = status.ownFavorite
                ? status.unfavorite()
                : status.favorite();
            promise.then(() => this._load()).catch((err) => {
                this._view.showError(err.message);
            });
        });

        this._view.addEventListener("repost", (e) => {
            const status = e.detail.status;
            status
                .repost()
                .then(() => {
                    this._view.showSuccess("Reposted!");
                })
                .catch((err) => {
                    this._view.showError(err.message);
                });
        });

        this._view.addEventListener("submitReply", (e) => {
            const { text, file, parentId } = e.detail;
            Status.create(text || "", file, parentId)
                .then((replyStatus) => {
                    this._view.addReply(replyStatus);
                    this._view.showSuccess("Reply posted!");
                })
                .catch((err) => {
                    this._view.showError(err.message);
                });
        });

        this._view.addEventListener("reply", (e) => {
            // Already handling replies via composer
        });

        this._view.addEventListener("edit", (e) => {
            this._load();
        });

        this._view.addEventListener("delete", (e) => {
            const status = e.detail.status;
            if (confirm("Delete this status?")) {
                status.delete()
                    .then(() => {
                        router.show(uri.formatClientLink("timeline"));
                    })
                    .catch((err) => {
                        this._view.showError(err.message);
                    });
            }
        });
    }
}

module.exports = (router) => {
    router.enter(["status", ":id"], (ctx, next) => {
        ctx.controller = new StatusDetailController(ctx);
    });
};
