"use strict";

const events = require("../events.js");
const views = require("../util/views.js");

const template = views.getTemplate("user-summary");

class UserSummaryView extends events.EventTarget {
    constructor(ctx) {
        super();
        this._hostNode = ctx.hostNode;
        this._ctx = ctx;
        views.replaceContent(this._hostNode, template(ctx));

        const followBtn = this._hostNode.querySelector(".follow-btn");
        if (followBtn) {
            followBtn.addEventListener("click", (e) => {
                e.preventDefault();
                this.dispatchEvent(new CustomEvent("follow"));
            });
        }
    }

    clearMessages() {
        views.clearMessages(this._hostNode);
    }

    showSuccess(message) {
        views.showSuccess(this._hostNode, message);
    }

    showError(message) {
        views.showError(this._hostNode, message);
    }

    enableForm() {
        const btn = this._hostNode.querySelector(".follow-btn");
        if (btn) btn.disabled = false;
    }

    disableForm() {
        const btn = this._hostNode.querySelector(".follow-btn");
        if (btn) btn.disabled = true;
    }
}

module.exports = UserSummaryView;
