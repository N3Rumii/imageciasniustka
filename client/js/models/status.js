"use strict";

const api = require("../api.js");
const uri = require("../util/uri.js");
const events = require("../events.js");

class Status extends events.EventTarget {
    constructor() {
        super();
        this._orig = {};
        this._updateFromResponse({});
    }

    get id() { return this._id; }
    get version() { return this._version; }
    get text() { return this._text; }
    get creationTime() { return this._creationTime; }
    get lastEditTime() { return this._lastEditTime; }
    get user() { return this._user; }
    get post() { return this._post; }
    get hashtags() { return this._hashtags; }
    get score() { return this._score; }
    get favoriteCount() { return this._favoriteCount; }
    get replyCount() { return this._replyCount; }
    get repostCount() { return this._repostCount; }
    get ownFavorite() { return this._ownFavorite; }
    get ownRepost() { return this._ownRepost; }
    get isRepost() { return this._isRepost; }
    get repostOriginal() { return this._repostOriginal; }
    get isReply() { return this._isReply; }
    get replyTo() { return this._replyTo; }
    get replies() { return this._replies; }
    get private() { return this._private; }

    set text(value) { this._text = value; }

    static fromResponse(response) {
        const ret = new Status();
        ret._updateFromResponse(response);
        return ret;
    }

    static get(id) {
        return api
            .get(uri.formatApiLink("status", id))
            .then((response) => Promise.resolve(Status.fromResponse(response)));
    }

    static getTimeline(params) {
        params = params || {};
        const queryParams = {};
        if (params.offset) queryParams.offset = params.offset;
        if (params.limit) queryParams.limit = params.limit;
        if (params.tag) queryParams.tag = params.tag;
        if (params.user) queryParams.user = params.user;
        if (params.feed) queryParams.feed = params.feed;
        if (params.sort) queryParams.sort = params.sort;
        return api
            .get(uri.formatApiLink("statuses", queryParams))
            .then((response) =>
                Promise.resolve(
                    (response.results || []).map((r) => Status.fromResponse(r))
                )
            );
    }

    static create(text, file, parentId, isPrivate) {
        const detail = {};
        if (text) detail.text = text;
        if (parentId) detail.parentId = parentId;
        if (isPrivate) detail.private = true;
        const files = {};
        if (file) files.content = file;
        return api
            .post(uri.formatApiLink("statuses"), detail, files)
            .then((response) => Promise.resolve(Status.fromResponse(response)));
    }

    save() {
        const detail = { version: this._version };
        if (this._text !== undefined) detail.text = this._text;
        return api
            .put(uri.formatApiLink("status", this._id), detail)
            .then((response) => {
                this._updateFromResponse(response);
                this.dispatchEvent(
                    new CustomEvent("change", { detail: { status: this } })
                );
                return Promise.resolve();
            });
    }

    delete() {
        return api
            .delete(uri.formatApiLink("status", this._id), {
                version: this._version,
            })
            .then(() => {
                this.dispatchEvent(
                    new CustomEvent("delete", { detail: { status: this } })
                );
                return Promise.resolve();
            });
    }

    favorite() {
        return api
            .post(uri.formatApiLink("status", this._id, "favorite"))
            .then((response) => {
                this._updateFromResponse(response);
                this.dispatchEvent(
                    new CustomEvent("change", { detail: { status: this } })
                );
                return Promise.resolve();
            });
    }

    unfavorite() {
        return api
            .delete(uri.formatApiLink("status", this._id, "favorite"))
            .then((response) => {
                this._updateFromResponse(response);
                this.dispatchEvent(
                    new CustomEvent("change", { detail: { status: this } })
                );
                return Promise.resolve();
            });
    }

    repost(text) {
        const body = {};
        if (text) body.text = text;
        return api
            .post(uri.formatApiLink("status", this._id, "repost"), body)
            .then((response) => {
                return Promise.resolve(Status.fromResponse(response));
            });
    }

    undoRepost() {
        return api
            .delete(uri.formatApiLink("status", this._id, "repost"))
            .then(() => {
                return Promise.resolve();
            });
    }

    getReplies() {
        return api
            .get(uri.formatApiLink("status", this._id, "replies"))
            .then((response) =>
                Promise.resolve(
                    (response.results || []).map((r) => Status.fromResponse(r))
                )
            );
    }

    _updateFromResponse(response) {
        const map = () => ({
            _id: response.id,
            _version: response.version,
            _text: response.text,
            _creationTime: response.creationTime,
            _lastEditTime: response.lastEditTime,
            _user: response.user,
            _post: response.post || null,
            _hashtags: response.hashtags || [],
            _score: response.score,
            _favoriteCount: response.favoriteCount,
            _replyCount: response.replyCount,
            _repostCount: response.repostCount,
            _ownFavorite: response.ownFavorite,
            _ownRepost: response.ownRepost || false,
            _isRepost: response.isRepost,
            _repostOriginal: response.repostOriginal,
            _isReply: response.isReply || false,
            _replyTo: response.replyTo || null,
            _replies: response.replies || [],
            _private: response.private || false,
        });
        Object.assign(this, map());
        this._orig = map();
    }
}

module.exports = Status;
