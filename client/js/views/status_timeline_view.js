"use strict";

const events = require("../events.js");
const views = require("../util/views.js");

const template = views.getTemplate("status-timeline");

class StatusTimelineView extends events.EventTarget {
    constructor() {
        super();
        this._hostNode = document.getElementById("content-holder");
        views.replaceContent(this._hostNode, template({}));
    }

    getHostNode() {
        return this._hostNode;
    }

    showSuccess(msg) {
        views.showSuccess(this._hostNode, msg);
    }

    showError(msg) {
        views.showError(this._hostNode, msg);
    }

    clearMessages() {
        views.clearMessages(this._hostNode);
    }
}

module.exports = StatusTimelineView;
