"use strict";

const router = require("../router.js");
const api = require("../api.js");
const misc = require("../util/misc.js");
const uri = require("../util/uri.js");
const GalleryCategoryList = require("../models/pool_category_list.js");
const GalleryCreateView = require("../views/pool_create_view.js");
const EmptyView = require("../views/empty_view.js");

class GalleryCreateController {
    constructor(ctx) {
        if (!api.hasPrivilege("pools:create")) {
            this._view = new EmptyView();
            this._view.showError("You don't have privileges to create galleries.");
            return;
        }

        GalleryCategoryList.get().then(
            (poolCategoriesResponse) => {
                const categories = {};
                for (let category of poolCategoriesResponse.results) {
                    categories[category.name] = category.name;
                }

                this._view = new GalleryCreateView({
                    canCreate: api.hasPrivilege("pools:create"),
                    categories: categories,
                    escapeTagName: uri.escapeTagName,
                });

                this._view.addEventListener("submit", (e) =>
                    this._evtCreate(e)
                );
            },
            (error) => {
                this._view = new EmptyView();
                this._view.showError(error.message);
            }
        );
    }

    _evtCreate(e) {
        this._view.clearMessages();
        this._view.disableForm();
        api.post(uri.formatApiLink("pool"), e.detail).then(
            () => {
                this._view.clearMessages();
                misc.disableExitConfirmation();
                const ctx = router.show(uri.formatClientLink("pools"));
                ctx.controller.showSuccess("Gallery created.");
            },
            (error) => {
                this._view.showError(error.message);
                this._view.enableForm();
            }
        );
    }
}

module.exports = (router) => {
    router.enter(["pool", "create"], (ctx, next) => {
        ctx.controller = new GalleryCreateController(ctx, "create");
    });
};
