"use strict";

const events = require("../events.js");
const api = require("../api.js");
const misc = require("../util/misc.js");
const views = require("../util/views.js");
const Gallery = require("../models/pool.js");

const template = views.getTemplate("pool-create");

class GalleryCreateView extends events.EventTarget {
    constructor(ctx) {
        super();

        this._hostNode = document.getElementById("content-holder");
        views.replaceContent(this._hostNode, template(ctx));

        views.decorateValidator(this._formNode);

        if (this._namesFieldNode) {
            this._namesFieldNode.addEventListener("input", (e) =>
                this._evtNameInput(e)
            );
        }

        if (this._postsFieldNode) {
            this._postsFieldNode.addEventListener("input", (e) =>
                this._evtPostsInput(e)
            );
        }

        for (let node of this._formNode.querySelectorAll(
            "input, select, textarea, posts"
        )) {
            node.addEventListener("change", (e) => {
                this.dispatchEvent(new CustomEvent("change"));
            });
        }

        this._formNode.addEventListener("submit", (e) => this._evtSubmit(e));

        // Toggle whitelist input visibility
        const privCheckbox = this._hostNode.querySelector("[name=private-gallery]");
        const whitelistDiv = this._hostNode.querySelector(".whitelist-input");
        if (privCheckbox && whitelistDiv) {
            privCheckbox.addEventListener("change", () => {
                whitelistDiv.style.display = privCheckbox.checked ? "block" : "none";
            });
        }
    }

    clearMessages() {
        views.clearMessages(this._hostNode);
    }

    enableForm() {
        views.enableForm(this._formNode);
    }

    disableForm() {
        views.disableForm(this._formNode);
    }

    showSuccess(message) {
        views.showSuccess(this._hostNode, message);
    }

    showError(message) {
        views.showError(this._hostNode, message);
    }

    _evtNameInput(e) {
        const regex = new RegExp(api.getGalleryNameRegex());
        const list = misc.splitByWhitespace(this._namesFieldNode.value);

        if (!list.length) {
            this._namesFieldNode.setCustomValidity(
                "Gallerys must have at least one name."
            );
            return;
        }

        for (let item of list) {
            if (!regex.test(item)) {
                this._namesFieldNode.setCustomValidity(
                    `Gallery name "${item}" contains invalid symbols.`
                );
                return;
            }
        }

        this._namesFieldNode.setCustomValidity("");
    }

    _evtPostsInput(e) {
        const regex = /^\d+$/;
        const value = this._postsFieldNode.value.replace(/,/g, " ");
        const list = misc.splitByWhitespace(value);

        for (let item of list) {
            if (!regex.test(item)) {
                this._postsFieldNode.setCustomValidity(
                    `Gallery ID "${item}" is not an integer.`
                );
                return;
            }
        }

        this._postsFieldNode.setCustomValidity("");
    }

    _evtSubmit(e) {
        e.preventDefault();

        const privCheckbox = this._hostNode.querySelector("[name=private-gallery]");
        const whitelistInput = this._hostNode.querySelector("[name=whitelist]");
        const whitelistRaw = whitelistInput ? whitelistInput.value : "";
        this.dispatchEvent(
            new CustomEvent("submit", {
                detail: {
                    names: misc.splitByWhitespace(this._namesFieldNode.value),
                    category: this._categoryFieldNode.value,
                    description: this._descriptionFieldNode.value,
                    posts: misc
                        .splitByWhitespace(
                            this._postsFieldNode.value.replace(/,/g, " ")
                        )
                        .map((i) => parseInt(i)),
                    private: privCheckbox ? privCheckbox.checked : false,
                    whitelist: whitelistRaw
                        .split(",")
                        .map((s) => s.trim())
                        .filter((s) => s.length > 0),
                },
            })
        );
    }

    get _formNode() {
        return this._hostNode.querySelector("form");
    }

    get _namesFieldNode() {
        return this._formNode.querySelector(".names input");
    }

    get _categoryFieldNode() {
        return this._formNode.querySelector(".category select");
    }

    get _descriptionFieldNode() {
        return this._formNode.querySelector(".description textarea");
    }

    get _postsFieldNode() {
        return this._formNode.querySelector(".posts input");
    }
}

module.exports = GalleryCreateView;
