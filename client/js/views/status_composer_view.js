"use strict";

const events = require("../events.js");
const views = require("../util/views.js");

const template = views.getTemplate("status-composer");

class StatusComposerView extends events.EventTarget {
    constructor(options) {
        super();
        options = options || {};
        this._parentStatus = options.parentStatus || null;
        this._initialText = options.text || "";
        this._file = null;
        this._imagePreview = null;
        this._hostNode = options.hostNode || document.getElementById("content-holder");
        this._render();
    }

    _render() {
        const ctx = {
            text: this._initialText,
            imagePreview: this._imagePreview,
            parentStatus: this._parentStatus,
        };
        views.replaceContent(this._hostNode, template(ctx));
        this._bindEvents();
    }

    _bindEvents() {
        const textarea = this._hostNode.querySelector(".status-composer-text");
        const fileInput = this._hostNode.querySelector(".status-composer-file");
        const submitBtn = this._hostNode.querySelector(".status-composer-submit");
        const cancelBtn = this._hostNode.querySelector(".status-composer-cancel-reply");
        const removeImgBtn = this._hostNode.querySelector(".status-composer-remove-image");
        const countSpan = this._hostNode.querySelector(".status-composer-count");

        if (textarea) {
            textarea.addEventListener("input", () => {
                const len = textarea.value.length;
                if (countSpan) countSpan.textContent = len + "/500";
                if (submitBtn) {
                    submitBtn.disabled = !textarea.value.trim() && !this._file;
                }
            });
            textarea.focus();
        }

        if (fileInput) {
            fileInput.addEventListener("change", () => {
                const file = fileInput.files[0];
                if (file) {
                    this._file = file;
                    // Save current text before re-rendering
                    const currentText = textarea ? textarea.value : "";
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        this._imagePreview = e.target.result;
                        this._initialText = currentText;
                        this._render();
                        // Restore focus and cursor position after re-render
                        const newTextarea = this._hostNode.querySelector(".status-composer-text");
                        if (newTextarea) {
                            newTextarea.focus();
                            newTextarea.setSelectionRange(currentText.length, currentText.length);
                        }
                    };
                    reader.readAsDataURL(file);
                }
            });
        }

        if (submitBtn) {
            submitBtn.addEventListener("click", (e) => {
                e.preventDefault();
                const text = textarea ? textarea.value.trim() : "";
                if (!text && !this._file) return;
                this.dispatchEvent(
                    new CustomEvent("submit", {
                        detail: {
                            text: text,
                            file: this._file,
                            parentId: this._parentStatus
                                ? this._parentStatus.id
                                : null,
                        },
                    })
                );
            });
        }

        if (cancelBtn) {
            cancelBtn.addEventListener("click", (e) => {
                e.preventDefault();
                this.dispatchEvent(new CustomEvent("cancelReply"));
            });
        }

        if (removeImgBtn) {
            removeImgBtn.addEventListener("click", (e) => {
                e.preventDefault();
                // Save current text before re-rendering
                const currentText = textarea ? textarea.value : "";
                this._file = null;
                this._imagePreview = null;
                this._initialText = currentText;
                this._render();
                const newTextarea = this._hostNode.querySelector(".status-composer-text");
                if (newTextarea) {
                    newTextarea.focus();
                    newTextarea.setSelectionRange(currentText.length, currentText.length);
                }
            });
        }

        // Submit on Ctrl+Enter
        if (textarea) {
            textarea.addEventListener("keydown", (e) => {
                if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault();
                    if (submitBtn && !submitBtn.disabled) submitBtn.click();
                }
            });
        }
    }
}

module.exports = StatusComposerView;
