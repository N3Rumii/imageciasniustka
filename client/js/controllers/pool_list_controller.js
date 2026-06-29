"use strict";

const router = require("../router.js");
const api = require("../api.js");
const uri = require("../util/uri.js");
const GalleryList = require("../models/pool_list.js");
const topNavigation = require("../models/top_navigation.js");
const PageController = require("../controllers/page_controller.js");
const GallerysHeaderView = require("../views/pools_header_view.js");
const GallerysPageView = require("../views/pools_page_view.js");
const EmptyView = require("../views/empty_view.js");

const fields = [
    "id",
    "names",
    "posts",
    "creationTime",
    "postCount",
    "category",
];

class GalleryListController {
    constructor(ctx) {
        this._pageController = new PageController();

        if (!api.hasPrivilege("pools:list")) {
            this._view = new EmptyView();
            this._view.showError("You don't have privileges to view galleries.");
            return;
        }

        this._ctx = ctx;

        topNavigation.activate("pools");
        topNavigation.setTitle("Listing galleries");

        this._headerView = new GallerysHeaderView({
            hostNode: this._pageController.view.pageHeaderHolderNode,
            parameters: ctx.parameters,
            canCreate: api.hasPrivilege("pools:create"),
            canEditGalleryCategories: api.hasPrivilege("poolCategories:edit"),
        });
        this._headerView.addEventListener(
            "submit",
            (e) => this._evtSubmit(e),
        );
        this._headerView.addEventListener(
            "navigate",
            (e) => this._evtNavigate(e)
        );

        this._syncPageController();
    }

    showSuccess(message) {
        this._pageController.showSuccess(message);
    }

    showError(message) {
        this._pageController.showError(message);
    }

    _evtSubmit(e) {
        this._view.clearMessages();
        this._view.disableForm();
        e.detail.pool.save().then(
            () => {
                this._installView(e.detail.pool, "edit");
                this._view.showSuccess("Gallery created.");
                router.replace(
                    uri.formatClientLink("pool", e.detail.pool.id, "edit"),
                    null,
                    false
                );
            },
            (error) => {
                this._view.showError(error.message);
                this._view.enableForm();
            }
        );
    }

    _evtNavigate(e) {
        router.showNoDispatch(
            uri.formatClientLink("pools", e.detail.parameters)
        );
        Object.assign(this._ctx.parameters, e.detail.parameters);
        this._syncPageController();
    }

    _syncPageController() {
        this._pageController.run({
            parameters: this._ctx.parameters,
            defaultLimit: 50,
            getClientUrlForPage: (offset, limit) => {
                const parameters = Object.assign({}, this._ctx.parameters, {
                    offset: offset,
                    limit: limit,
                });
                return uri.formatClientLink("pools", parameters);
            },
            requestPage: (offset, limit) => {
                return GalleryList.search(
                    this._ctx.parameters.query,
                    offset,
                    limit,
                    fields,
                    {}
                );
            },
            pageRenderer: (pageCtx) => {
                return new GallerysPageView(pageCtx);
            },
        });
    }
}

module.exports = (router) => {
    router.enter(["pools"], (ctx, next) => {
        ctx.controller = new GalleryListController(ctx);
    });
};
