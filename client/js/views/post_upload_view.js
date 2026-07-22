"use strict";

const events = require("../events.js");
const api = require("../api.js");
const views = require("../util/views.js");
const misc = require("../util/misc.js");
const FileDropperControl = require("../controls/file_dropper_control.js");
const TagList = require("../models/tag_list.js");
const TagInputControl = require("../controls/tag_input_control.js");
const UserAutoCompleteControl = require("../controls/user_auto_complete_control.js");

const template = views.getTemplate("post-upload");
const rowTemplate = views.getTemplate("post-upload-row");

function _mimeTypeToPostType(mimeType) {
    return (
        {
            "application/x-shockwave-flash": "flash",
            "image/gif": "image",
            "image/jpeg": "image",
            "image/png": "image",
            "image/webp": "image",
            "image/bmp": "image",
            "image/avif": "image",
            "image/heif": "image",
            "image/heic": "image",
            "video/mp4": "video",
            "video/webm": "video",
            "video/quicktime": "video",
        }[mimeType] || "unknown"
    );
}

class Uploadable extends events.EventTarget {
    constructor() {
        super();
        this.lookalikes = [];
        this.lookalikesConfirmed = false;
        this.safety = "safe";
        this.flags = [];
        this.tags = [];
        this.relations = [];
        this.anonymous = !api.isLoggedIn();
        this.forceAnonymous = !api.isLoggedIn();
    }

    destroy() {}

    get mimeType() {
        return "application/octet-stream";
    }

    get type() {
        return _mimeTypeToPostType(this.mimeType);
    }

    get key() {
        throw new Error("Not implemented");
    }

    get name() {
        throw new Error("Not implemented");
    }
}

class File extends Uploadable {
    constructor(file) {
        super();
        this.file = file;

        this._previewUrl = null;
        // Skip preview for files > 5 MB to avoid freezing the browser
        // (especially animated GIFs which can be 38+ MB and crash the tab)
        if (file.size <= 5 * 1024 * 1024) {
            if (URL && URL.createObjectURL) {
                this._previewUrl = URL.createObjectURL(file);
            } else {
                let reader = new FileReader();
                reader.readAsDataURL(file);
                reader.addEventListener("load", (e) => {
                    this._previewUrl = e.target.result;
                    this.dispatchEvent(
                        new CustomEvent("finish", {
                            detail: { uploadable: this },
                        })
                    );
                });
            }
        }
    }

    destroy() {
        if (URL && URL.createObjectURL && URL.revokeObjectURL) {
            URL.revokeObjectURL(this._previewUrl);
        }
    }

    get mimeType() {
        return this.file.type;
    }

    get previewUrl() {
        return this._previewUrl;
    }

    get key() {
        return this.file.name + this.file.size;
    }

    get name() {
        return this.file.name;
    }
}

class Url extends Uploadable {
    constructor(url) {
        super();
        this.url = url;
        this.dispatchEvent(new CustomEvent("finish"));
    }

    get mimeType() {
        let mime = {
            swf: "application/x-shockwave-flash",
            jpg: "image/jpeg",
            png: "image/png",
            gif: "image/gif",
            webp: "image/webp",
            bmp: "image/bmp",
            avif: "image/avif",
            heif: "image/heif",
            heic: "image/heic",
            mp4: "video/mp4",
            mov: "video/quicktime",
            webm: "video/webm",
        };
        for (let extension of Object.keys(mime)) {
            if (this.url.toLowerCase().indexOf("." + extension) !== -1) {
                return mime[extension];
            }
        }
        return "unknown";
    }

    get previewUrl() {
        return this.url;
    }

    get key() {
        return this.url;
    }

    get name() {
        return this.url;
    }
}

class PostUploadView extends events.EventTarget {
    constructor(ctx) {
        super();
        this._ctx = ctx;
        this._hostNode = document.getElementById("content-holder");

        views.replaceContent(this._hostNode, template());
        views.syncScrollPosition();

        this._cancelButtonNode.disabled = true;

        this._uploadables = [];
        this._uploadables.find = (u) => {
            return this._uploadables.findIndex((u2) => u.key === u2.key);
        };

        this._contentFileDropper = new FileDropperControl(
            this._contentInputNode,
            {
                extraText:
                    "Allowed extensions: .jpg, .png, .gif, .webm, .mp4, .swf, .avif, .heif, .heic",
                allowUrls: true,
                allowMultiple: true,
                lock: false,
            }
        );
        this._contentFileDropper.addEventListener("fileadd", (e) =>
            this._evtFilesAdded(e)
        );
        this._contentFileDropper.addEventListener("urladd", (e) =>
            this._evtUrlsAdded(e)
        );

        this._cancelButtonNode.addEventListener("click", (e) =>
            this._evtCancelButtonClick(e)
        );
        this._formNode.addEventListener("submit", (e) =>
            this._evtFormSubmit(e)
        );
        this._formNode.classList.add("inactive");

        // Global tag input — tags applied to every uploaded file
        this._globalTagList = new TagList();
        const globalTagsHost = this._hostNode.querySelector(".global-tags-input");
        this._globalTagInput = new TagInputControl(globalTagsHost, this._globalTagList);

        // Whitelist user input with auto-complete (tag-style, like chat room creation)
        this._whitelistUsers = [];
        const whitelistInput = this._hostNode.querySelector(".whitelist-users-input");
        const whitelistSuggestions = this._hostNode.querySelector(".whitelist-suggestions");
        if (whitelistInput) {
            this._whitelistAutoComplete = new UserAutoCompleteControl(
                whitelistInput,
                {
                    confirm: (user) => {
                        if (user && user.name && !this._whitelistUsers.includes(user.name)) {
                            this._whitelistUsers.push(user.name);
                            this._renderWhitelistTags();
                        }
                        whitelistInput.value = "";
                    },
                }
            );
            whitelistInput.addEventListener("keydown", (e) => {
                if (e.key === "Enter" || e.key === ",") {
                    e.preventDefault();
                    const name = whitelistInput.value.trim();
                    if (name && !this._whitelistUsers.includes(name)) {
                        this._whitelistUsers.push(name);
                        this._renderWhitelistTags();
                    }
                    whitelistInput.value = "";
                }
                if (e.key === "Backspace" && !whitelistInput.value && this._whitelistUsers.length) {
                    this._whitelistUsers.pop();
                    this._renderWhitelistTags();
                }
            });
        }

        // Toggle whitelist input visibility on private checkbox
        if (this._privateCheckboxNode && this._whitelistInputNode) {
            this._privateCheckboxNode.addEventListener("change", () => {
                this._whitelistInputNode.style.display =
                    this._privateCheckboxNode.checked ? "inline" : "none";
            });
        }
    }

    enableForm() {
        views.enableForm(this._formNode);
        this._cancelButtonNode.disabled = true;
        this._formNode.classList.remove("uploading");
    }

    disableForm() {
        views.disableForm(this._formNode);
        this._cancelButtonNode.disabled = false;
        this._formNode.classList.add("uploading");
    }

    clearMessages() {
        views.clearMessages(this._hostNode);
    }

    showSuccess(message) {
        views.showSuccess(this._hostNode, message);
    }

    showError(message, uploadable) {
        this._showMessage(views.showError, message, uploadable);
    }

    showInfo(message, uploadable) {
        this._showMessage(views.showInfo, message, uploadable);
        views.appendExclamationMark();
    }

    _showMessage(functor, message, uploadable) {
        functor(uploadable ? uploadable.rowNode : this._hostNode, message);
    }

    addUploadables(uploadables) {
        this._formNode.classList.remove("inactive");
        let duplicatesFound = 0;
        for (let uploadable of uploadables) {
            if (this._uploadables.find(uploadable) !== -1) {
                duplicatesFound++;
                continue;
            }
            this._uploadables.push(uploadable);
            this._emit("change");
            this._renderRowNode(uploadable);
            uploadable.addEventListener("finish", (e) =>
                this._updateThumbnailNode(e.detail.uploadable)
            );
        }
        if (duplicatesFound) {
            let message = null;
            if (duplicatesFound < uploadables.length) {
                message =
                    "Some of the files were already added " +
                    "and have been skipped.";
            } else if (duplicatesFound === 1) {
                message = "This file was already added.";
            } else {
                message = "These files were already added.";
            }
            alert(message);
        }
    }

    removeUploadable(uploadable) {
        if (this._uploadables.find(uploadable) === -1) {
            return;
        }
        uploadable.destroy();
        // Clean up per-file tag input DOM (TagInputControl inserts after host)
        if (uploadable._tagInputControl && uploadable._tagInputControl._editAreaNode) {
            const editNode = uploadable._tagInputControl._editAreaNode;
            if (editNode.parentNode) editNode.parentNode.removeChild(editNode);
        }
        uploadable.rowNode.parentNode.removeChild(uploadable.rowNode);
        this._uploadables.splice(this._uploadables.find(uploadable), 1);
        this._emit("change");
        if (!this._uploadables.length) {
            this._formNode.classList.add("inactive");
            this._submitButtonNode.value = "Upload all";
        }
    }

    updateUploadable(uploadable) {
        uploadable.lookalikesConfirmed = true;
        this._renderRowNode(uploadable);
    }

    _evtFilesAdded(e) {
        this.addUploadables(e.detail.files.map((file) => new File(file)));
    }

    _evtUrlsAdded(e) {
        this.addUploadables(e.detail.urls.map((url) => new Url(url)));
    }

    _evtCancelButtonClick(e) {
        e.preventDefault();
        this._emit("cancel");
    }

    _evtFormSubmit(e) {
        e.preventDefault();
        for (let uploadable of this._uploadables) {
            this._updateUploadableFromDom(uploadable);
        }
        this._submitButtonNode.value = "Resume";
        this._emit("submit");
    }

    _updateUploadableFromDom(uploadable) {
        const rowNode = uploadable.rowNode;

        const safetyNode = rowNode.querySelector(".safety input:checked");
        if (safetyNode) {
            uploadable.safety = safetyNode.value;
        }

        const anonymousNode = rowNode.querySelector(
            ".anonymous input:checked"
        );
        if (anonymousNode) {
            uploadable.anonymous = true;
        }

        // Read per-file tags from the TagList managed by TagInputControl
        uploadable.tags = (uploadable._tagList
            ? [...uploadable._tagList].map((t) => t.names[0])
            : []);

        uploadable.relations = [];
        for (let [i, lookalike] of uploadable.lookalikes.entries()) {
            if (!lookalike || !lookalike.post) { continue; }
            let lookalikeNode = rowNode.querySelector(
                `.lookalikes li:nth-child(${i + 1})`
            );
            // Merge lookalike copy-tags into per-file tags
            if (lookalikeNode.querySelector("[name=copy-tags]").checked) {
                uploadable.tags = uploadable.tags.concat(
                    lookalike.post.tagNames
                );
            }
            if (lookalikeNode.querySelector("[name=add-relation]").checked) {
                uploadable.relations.push(lookalike.post.id);
            }
        }
    }

    _evtRemoveClick(e, uploadable) {
        e.preventDefault();
        if (this._uploading) {
            return;
        }
        this.removeUploadable(uploadable);
    }

    _evtMoveClick(e, uploadable, delta) {
        e.preventDefault();
        if (this._uploading) {
            return;
        }
        let index = this._uploadables.find(uploadable);
        if ((index + delta).between(-1, this._uploadables.length)) {
            let uploadable1 = this._uploadables[index];
            let uploadable2 = this._uploadables[index + delta];
            this._uploadables[index] = uploadable2;
            this._uploadables[index + delta] = uploadable1;
            if (delta === 1) {
                this._listNode.insertBefore(
                    uploadable2.rowNode,
                    uploadable1.rowNode
                );
            } else {
                this._listNode.insertBefore(
                    uploadable1.rowNode,
                    uploadable2.rowNode
                );
            }
        }
    }

    _emit(eventType) {
        this.dispatchEvent(
            new CustomEvent(eventType, {
                detail: {
                    uploadables: this._uploadables,
                    skipDuplicates: this._skipDuplicatesCheckboxNode.checked,
                    alwaysUploadSimilar:
                        this._alwaysUploadSimilarCheckboxNode.checked,
                    pauseRemainOnError:
                        this._pauseRemainOnErrorCheckboxNode.checked,
                    isPrivate:
                        this._privateCheckboxNode
                            ? this._privateCheckboxNode.checked
                            : false,
                    whitelistUsernames: this._getWhitelistUsernames(),
                    globalTags: [...this._globalTagList].map((t) => t.names[0]),
                },
            })
        );
    }

    _renderRowNode(uploadable) {
        const rowNode = rowTemplate(
            Object.assign({}, this._ctx, { uploadable: uploadable })
        );
        if (uploadable.rowNode) {
            uploadable.rowNode.parentNode.replaceChild(
                rowNode,
                uploadable.rowNode
            );
        } else {
            this._listNode.appendChild(rowNode);
        }

        uploadable.rowNode = rowNode;

        // Per-file tag input — create a TagList + TagInputControl for this uploadable
        if (!uploadable._tagList) {
            uploadable._tagList = new TagList();
        }
        const perFileHost = rowNode.querySelector(".per-file-tags-input");
        if (perFileHost) {
            // Clean up previous TagInputControl DOM if re-rendering
            if (uploadable._tagInputControl && uploadable._tagInputControl._editAreaNode) {
                const oldNode = uploadable._tagInputControl._editAreaNode;
                if (oldNode.parentNode) oldNode.parentNode.removeChild(oldNode);
            }
            uploadable._tagInputControl = new TagInputControl(
                perFileHost, uploadable._tagList
            );
        }

        rowNode
            .querySelector("a.remove")
            .addEventListener("click", (e) =>
                this._evtRemoveClick(e, uploadable)
            );
        rowNode
            .querySelector("a.move-up")
            .addEventListener("click", (e) =>
                this._evtMoveClick(e, uploadable, -1)
            );
        rowNode
            .querySelector("a.move-down")
            .addEventListener("click", (e) =>
                this._evtMoveClick(e, uploadable, 1)
            );
    }

    _updateThumbnailNode(uploadable) {
        const rowNode = rowTemplate(
            Object.assign({}, this._ctx, { uploadable: uploadable })
        );
        views.replaceContent(
            uploadable.rowNode.querySelector(".thumbnail"),
            rowNode.querySelector(".thumbnail").childNodes
        );
    }

    get _uploading() {
        return this._formNode.classList.contains("uploading");
    }

    get _listNode() {
        return this._hostNode.querySelector(".uploadables-container");
    }

    get _formNode() {
        return this._hostNode.querySelector("form");
    }

    get _skipDuplicatesCheckboxNode() {
        return this._hostNode.querySelector("form [name=skip-duplicates]");
    }

    get _alwaysUploadSimilarCheckboxNode() {
        return this._hostNode.querySelector(
            "form [name=always-upload-similar]"
        );
    }

    get _pauseRemainOnErrorCheckboxNode() {
        return this._hostNode.querySelector(
            "form [name=pause-remain-on-error]"
        );
    }

    get _submitButtonNode() {
        return this._hostNode.querySelector("form [type=submit]");
    }

    get _cancelButtonNode() {
        return this._hostNode.querySelector("form .cancel");
    }

    get _contentInputNode() {
        return this._formNode.querySelector(".dropper-container");
    }

    get _privateCheckboxNode() {
        return this._hostNode.querySelector("form [name=private-post]");
    }

    get _whitelistInputNode() {
        return this._hostNode.querySelector("form .whitelist-input");
    }

    _getWhitelistUsernames() {
        return [...this._whitelistUsers];
    }

    _renderWhitelistTags() {
        const container = this._hostNode.querySelector(".whitelist-users-tags");
        if (!container) return;
        container.innerHTML = "";
        for (const name of this._whitelistUsers) {
            const tag = document.createElement("span");
            tag.className = "user-tag";
            tag.innerHTML =
                misc.escapeHtml(name) +
                '<span class="remove-tag" data-name="' +
                misc.escapeHtml(name) +
                '">\u00d7</span>';
            tag.querySelector(".remove-tag").addEventListener("click", () => {
                this._whitelistUsers = this._whitelistUsers.filter(
                    (n) => n !== name
                );
                this._renderWhitelistTags();
            });
            container.appendChild(tag);
        }
    }
}

module.exports = PostUploadView;
