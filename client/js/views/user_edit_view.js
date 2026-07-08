"use strict";

const events = require("../events.js");
const api = require("../api.js");
const views = require("../util/views.js");
const FileDropperControl = require("../controls/file_dropper_control.js");

const template = views.getTemplate("user-edit");

class UserEditView extends events.EventTarget {
    constructor(ctx) {
        super();

        ctx.userNamePattern = api.getUserNameRegex() + /|^$/.source;
        ctx.passwordPattern = api.getPasswordRegex() + /|^$/.source;

        this._user = ctx.user;
        this._hostNode = ctx.hostNode;
        views.replaceContent(this._hostNode, template(ctx));
        views.decorateValidator(this._formNode);

        this._avatarContent = null;
        if (this._avatarContentInputNode) {
            this._avatarFileDropper = new FileDropperControl(
                this._avatarContentInputNode,
                { lock: true }
            );
            this._avatarFileDropper.addEventListener("fileadd", (e) => {
                this._hostNode.querySelector(
                    "[name=avatar-style][value=manual]"
                ).checked = true;
                this._avatarContent = e.detail.files[0];
            });
        }

        for (let node of this._formNode.querySelectorAll("input, select")) {
            node.addEventListener("change", (e) => {
                if (!e.target.classList.contains("anticomplete")) {
                    this.dispatchEvent(new CustomEvent("change"));
                }
            });
        }

        // Wire preset swatches
        for (let swatch of this._hostNode.querySelectorAll(".preset-swatch")) {
            swatch.addEventListener("click", (e) => {
                var colorInput = this._hostNode.querySelector("#profile-accent");
                if (colorInput) colorInput.value = swatch.getAttribute("data-color");
            });
        }

        // Wire CSS preset buttons
        for (let btn of this._hostNode.querySelectorAll(".css-preset-btn")) {
            btn.addEventListener("click", (e) => {
                var cssInput = this._hostNode.querySelector("#profile-css");
                if (cssInput) cssInput.value = btn.getAttribute("data-css");
            });
        }

        // Wire CSS section merging — collect all section textareas into main field on submit
        var cssMain = this._hostNode.querySelector("#profile-css");
        var cssSections = this._hostNode.querySelectorAll(".css-area");
        for (let section of cssSections) {
            // Load saved CSS into matching section on init
            var key = section.getAttribute("data-css-key");
            var savedCss = cssMain ? cssMain.value : "";
            // Simple extraction: look for section comment markers if present
            section.value = "";  // Start fresh; user fills manually
        }
        // On form submit, merge sections into main CSS field
        if (cssMain) {
            this._formNode.addEventListener("submit", function() {
                var parts = [];
                for (let section of cssSections) {
                    var val = section.value.trim();
                    if (val) parts.push("/* " + section.getAttribute("data-css-key") + " */\n" + val);
                }
                var rawCss = cssMain.value.trim();
                if (rawCss) parts.push("/* raw */\n" + rawCss);
                cssMain.value = parts.join("\n\n");
            });
        }

        // Wire header upload
        var headerUpload = this._hostNode.querySelector("#profile-header-upload");
        var headerInput = this._hostNode.querySelector("#profile-header-input");
        if (headerUpload && headerInput) {
            headerUpload.addEventListener("click", () => {
                var file = headerInput.files[0];
                if (!file) return;
                this._headerFile = file;
                var preview = this._hostNode.querySelector("#header-preview");
                if (preview) {
                    preview.style.backgroundImage = "url(" + URL.createObjectURL(file) + ")";
                }
                headerUpload.textContent = "✓ Selected";
            });
        }

        this._formNode.addEventListener("submit", (e) => this._evtSubmit(e));
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
        views.enableForm(this._formNode);
    }

    disableForm() {
        views.disableForm(this._formNode);
    }

    _evtSubmit(e) {
        e.preventDefault();
        this.dispatchEvent(
            new CustomEvent("submit", {
                detail: {
                    user: this._user,

                    name: this._userNameInputNode
                        ? this._userNameInputNode.value
                        : undefined,

                    email: this._emailInputNode
                        ? this._emailInputNode.value
                        : undefined,

                    rank: this._rankInputNode
                        ? this._rankInputNode.value
                        : undefined,

                    avatarStyle: this._avatarStyleInputNode
                        ? this._avatarStyleInputNode.value
                        : undefined,

                    password: this._passwordInputNode
                        ? this._passwordInputNode.value
                        : undefined,

                    avatarContent: this._avatarContent,

                    profileBio: this._formNode.querySelector("[name=profile-bio]")
                        ? this._formNode.querySelector("[name=profile-bio]").value
                        : undefined,

                    profileCss: this._formNode.querySelector("[name=profile-css]")
                        ? this._formNode.querySelector("[name=profile-css]").value
                        : undefined,

                    profileAccentColor: this._formNode.querySelector("[name=profile-accent]")
                        ? this._formNode.querySelector("[name=profile-accent]").value
                        : undefined,

                    profileLayout: this._formNode.querySelector("[name=profile-layout]")
                        ? this._formNode.querySelector("[name=profile-layout]").value
                        : undefined,

                    profileEmbeds: this._formNode.querySelector("[name=profile-embeds]")
                        ? this._formNode.querySelector("[name=profile-embeds]").value
                        : undefined,

                    profileAbout: this._formNode.querySelector("[name=profile-about]")
                        ? this._formNode.querySelector("[name=profile-about]").value
                        : undefined,

                    profileLinks: this._formNode.querySelector("[name=profile-links]")
                        ? this._formNode.querySelector("[name=profile-links]").value
                        : undefined,

                    headerFile: this._headerFile || null,
                },
            })
        );
    }

    get _formNode() {
        return this._hostNode.querySelector("form");
    }

    get _rankInputNode() {
        return this._formNode.querySelector("[name=rank]");
    }

    get _emailInputNode() {
        return this._formNode.querySelector("[name=email]");
    }

    get _userNameInputNode() {
        return this._formNode.querySelector("[name=name]");
    }

    get _passwordInputNode() {
        return this._formNode.querySelector("[name=password]");
    }

    get _avatarContentInputNode() {
        return this._formNode.querySelector("#avatar-content");
    }

    get _avatarStyleInputNode() {
        return this._formNode.querySelector("[name=avatar-style]:checked");
    }
}

module.exports = UserEditView;
