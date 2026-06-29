"use strict";

const api = require("../api.js");
const galleries = require("../pools.js");
const GalleryCategoryList = require("../models/pool_category_list.js");
const topNavigation = require("../models/top_navigation.js");
const GalleryCategoriesView = require("../views/pool_categories_view.js");
const EmptyView = require("../views/empty_view.js");

class GalleryCategoriesController {
    constructor() {
        if (!api.hasPrivilege("poolCategories:list")) {
            this._view = new EmptyView();
            this._view.showError(
                "You don't have privileges to view pool categories."
            );
            return;
        }

        topNavigation.activate("pools");
        topNavigation.setTitle("Listing galleries");
        GalleryCategoryList.get().then(
            (response) => {
                this._poolCategories = response.results;
                this._view = new GalleryCategoriesView({
                    poolCategories: this._poolCategories,
                    canEditName: api.hasPrivilege("poolCategories:edit:name"),
                    canEditColor: api.hasPrivilege(
                        "poolCategories:edit:color"
                    ),
                    canDelete: api.hasPrivilege("poolCategories:delete"),
                    canCreate: api.hasPrivilege("poolCategories:create"),
                    canSetDefault: api.hasPrivilege(
                        "poolCategories:setDefault"
                    ),
                });
                this._view.addEventListener("submit", (e) =>
                    this._evtSubmit(e)
                );
            },
            (error) => {
                this._view = new EmptyView();
                this._view.showError(error.message);
            }
        );
    }

    _evtSubmit(e) {
        this._view.clearMessages();
        this._view.disableForm();
        this._poolCategories.save().then(
            () => {
                galleries.refreshCategoryColorMap();
                this._view.enableForm();
                this._view.showSuccess("Changes saved.");
            },
            (error) => {
                this._view.enableForm();
                this._view.showError(error.message);
            }
        );
    }
}

module.exports = (router) => {
    router.enter(["pool-categories"], (ctx, next) => {
        ctx.controller = new GalleryCategoriesController(ctx, next);
    });
};
