"use strict";

const api = require("../api.js");

/** Redirect to chat.ciasniutka.pl with auth token in URL fragment. */
class ChatRedirectController {
    constructor() {
        const userName = api.userName;
        const authToken = api.token;  // login token (UUID), not raw password
        if (userName && authToken) {
            // Use token auth: base64(user:token)
            const encoded = btoa(userName + ":" + authToken);
            window.location.href = "/chat/#token=" + encoded;
        } else if (userName && api.userPassword) {
            // Fallback: use password auth if token isn't available
            const encoded = btoa(userName + ":" + api.userPassword);
            window.location.href = "/chat/#token=" + encoded;
        } else {
            // Not logged in — redirect to chat with login prompt
            window.location.href = "/chat/";
        }
    }
}

module.exports = function(router) {
    router.enter(["chat"], function(ctx, next) {
        ctx.controller = new ChatRedirectController(ctx);
    });
    router.enter(["messages"], function(ctx, next) {
        ctx.controller = new ChatRedirectController(ctx);
    });
};
