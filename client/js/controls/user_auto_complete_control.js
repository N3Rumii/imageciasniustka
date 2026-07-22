"use strict";

const misc = require("../util/misc.js");
const views = require("../util/views.js");
const UserList = require("../models/user_list.js");
const AutoCompleteControl = require("./auto_complete_control.js");

/**
 * Auto-complete for usernames — used by whitelist input and room creation.
 * Extends AutoCompleteControl, searches /api/users/ for matches.
 */
class UserAutoCompleteControl extends AutoCompleteControl {
    constructor(input, options) {
        options = Object.assign(
            {
                maxResults: 10,
                getMatches: (text) => {
                    if (!text || text.length < 1) {
                        return new Promise((resolve) => resolve([]));
                    }
                    const term = misc.escapeSearchTerm(text);
                    const query = "*" + term + "*";

                    return new Promise((resolve, reject) => {
                        UserList.search(query, 0, options.maxResults, [], {
                            noProgress: true,
                        }).then(
                            (response) => {
                                const matches = (response.results || [])
                                    .map((user) => {
                                        user.matchingName = user.name;
                                        const caption =
                                            '<span class="user-autocomplete-item">' +
                                            misc.escapeHtml(user.name) +
                                            "</span>";
                                        return {
                                            caption: caption,
                                            value: user,
                                        };
                                    });
                                resolve(matches);
                            },
                            reject
                        );
                    });
                },
            },
            options
        );

        super(input, options);
    }

    _getActiveSuggestion() {
        if (this._activeResult === -1) {
            return null;
        }
        return this._results[this._activeResult].value;
    }
}

module.exports = UserAutoCompleteControl;
