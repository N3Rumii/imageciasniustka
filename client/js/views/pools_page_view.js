"use strict";

const views = require("../util/views.js");

const template = views.getTemplate("pools-page");

class GallerysPageView {
    constructor(ctx) {
        views.replaceContent(ctx.hostNode, template(ctx));
    }
}

module.exports = GallerysPageView;
