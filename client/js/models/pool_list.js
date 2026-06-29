"use strict";

const api = require("../api.js");
const uri = require("../util/uri.js");
const AbstractList = require("./abstract_list.js");
const Gallery = require("./pool.js");

class GalleryList extends AbstractList {
    static search(text, offset, limit, fields, options) {
        return api
            .get(
                uri.formatApiLink("pools", {
                    query: text,
                    offset: offset,
                    limit: limit,
                    fields: fields.join(","),
                }),
                options
            )
            .then((response) => {
                return Promise.resolve(
                    Object.assign({}, response, {
                        results: GalleryList.fromResponse(response.results),
                    })
                );
            });
    }

    hasGalleryId(poolId) {
        for (let pool of this._list) {
            if (pool.id === poolId) {
                return true;
            }
        }
        return false;
    }

    removeById(poolId) {
        for (let pool of this._list) {
            if (pool.id === poolId) {
                this.remove(pool);
            }
        }
    }
}

GalleryList._itemClass = Gallery;
GalleryList._itemName = "pool";

module.exports = GalleryList;
