"use strict";

const views = require("../util/views.js");
const api = require("../api.js");
const uri = require("../util/uri.js");

const template = views.getTemplate("users-page");

class UsersPageView {
    constructor(ctx) {
        this._ctx = ctx;
        views.replaceContent(ctx.hostNode, template(ctx));
        this._wireBlockButtons();
    }

    _wireBlockButtons() {
        const hostNode = this._ctx.hostNode;
        const buttons = hostNode.querySelectorAll(".block-btn");
        for (const btn of buttons) {
            btn.addEventListener("click", (e) => {
                e.preventDefault();
                const userName = btn.getAttribute("data-user");
                const isBlocked = btn.classList.contains("unblock");
                this._toggleBlock(userName, isBlocked, btn);
            });
        }
    }

    _toggleBlock(userName, isCurrentlyBlocked, btn) {
        btn.disabled = true;

        var url = uri.formatApiLink("user", userName, "block");
        var promise = isCurrentlyBlocked
            ? api.delete(url)
            : api.post(url);

        promise
            .then(function () {
                if (isCurrentlyBlocked) {
                    btn.classList.remove("unblock");
                    btn.classList.add("block");
                    btn.textContent = "Block";
                } else {
                    btn.classList.remove("block");
                    btn.classList.add("unblock");
                    btn.textContent = "Unblock";
                }
            })
            .catch(function (err) {
                window.alert("Block failed: " + (err.message || JSON.stringify(err)));
                btn.disabled = false;
            })
            .finally(function () {
                btn.disabled = false;
            });
    }
}

module.exports = UsersPageView;
