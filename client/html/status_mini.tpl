<div class="status-mini<%= ctx.status.isRepost ? ' status-mini-is-repost' : '' %><%= ctx.isReply ? ' status-mini-is-reply' : '' %>" data-status-id="<%- ctx.status.id %>"<%= ctx.isReply ? ' style="margin-left:' + ((ctx.nestLevel || 1) * 20) + 'px"' : '' %>>
    <% if (ctx.status.user) { %>
    <div class="status-mini-avatar">
        <a href="<%- ctx.formatClientLink('user', ctx.status.user.name) %>">
            <img src="<%- ctx.status.user.avatarUrl %>" alt="<%- ctx.status.user.name %>" />
        </a>
    </div>
    <% } %>
    <div class="status-mini-body">
        <% if (ctx.status.user) { %>
        <div class="status-mini-header">
            <a class="status-mini-user" href="<%- ctx.formatClientLink('user', ctx.status.user.name) %>">
                <%- ctx.status.user.name %>
            </a>
            <span class="status-mini-time">
                <%= ctx.makeRelativeTime(ctx.status.creationTime) %>
            </span>
            <% if (ctx.status.lastEditTime) { %>
                <span class="status-mini-edited">(edited)</span>
            <% } %>
            <% if (ctx.status.private) { %>
                <i class="fa fa-lock status-mini-lock"></i>
            <% } %>
        </div>
        <% } %>
        <% if (ctx.isReply && ctx.replyToName) { %>
            <div class="status-mini-reply-to">Replying to <a href="<%- ctx.formatClientLink('status', ctx.status.replyTo.id) %>">@<%- ctx.replyToName %></a></div>
        <% } %>
        <% if (ctx.status.text) { %>
            <div class="status-mini-text"><%= ctx.makeMarkdown(ctx.status.text) %></div>
        <% } %>
        <% if (ctx.status.isRepost) { %>
            <div class="status-mini-reposted">
                <i class="fa fa-retweet"></i> Reposted
                <% if (ctx.status.repostOriginal && ctx.status.repostOriginal.user) { %>
                    from <a href="<%- ctx.formatClientLink('user', ctx.status.repostOriginal.user.name) %>"><%- ctx.status.repostOriginal.user.name %></a>
                    <% if (ctx.status.repostOriginal.text) { %>
                        <div class="status-mini-repost-text"><%= ctx.makeMarkdown(ctx.status.repostOriginal.text) %></div>
                    <% } %>
                <% } %>
            </div>
        <% } %>
        <% if (!ctx.isReply) { %>
        <% if (ctx.status.isReply) { %>
            <div class="status-mini-reply">
                <i class="fa fa-reply"></i> Responds to
                <% if (ctx.status.replyTo) { %>
                    <a href="<%- ctx.formatClientLink('status', ctx.status.replyTo.id) %>">
                        <% if (ctx.status.replyTo.user) { %><%- ctx.status.replyTo.user.name %><% } %>
                    </a>
                <% } %>
            </div>
        <% } %>
        <% } %>
        <% if (ctx.status.post) { %>
            <% if (ctx.status.post.type === 'video') { %>
                <div class="status-mini-video">
                    <video class="status-mini-video-player" controls preload="metadata" src="<%- ctx.status.post.contentUrl %>" poster="<%- ctx.status.post.thumbnailUrl %>">
                        Your browser does not support video.
                    </video>
                </div>
            <% } else { %>
                <a class="status-mini-image-link" href="<%- ctx.formatClientLink('post', ctx.status.post.id) %>">
                    <img class="status-mini-image" src="<%- ctx.status.post.thumbnailUrl %>" alt="Post #<%- ctx.status.post.id %>" />
                </a>
            <% } %>
        <% } %>
        <div class="status-mini-actions<%= ctx.isReply ? ' status-mini-actions-compact' : '' %>">
            <% if (!ctx.isReply) { %>
            <button class="status-mini-action status-mini-reply" data-action="reply" title="Reply">
                <i class="fa fa-reply"></i> <span class="count"><%- ctx.status.replyCount %></span>
            </button>
            <% } %>
            <button class="status-mini-action status-mini-favorite<%= ctx.status.ownFavorite ? ' active' : '' %>" data-action="favorite" title="Like">
                <i class="fa fa-heart"></i><% if (!ctx.isReply) { %> <span class="count"><%- ctx.status.favoriteCount %></span><% } %>
            </button>
            <button class="status-mini-action status-mini-repost" data-action="repost" title="Repost">
                <i class="fa fa-retweet"></i><% if (!ctx.isReply) { %> <span class="count"><%- ctx.status.repostCount %></span><% } %>
            </button>
            <div class="status-mini-menu">
                <button class="status-mini-action status-mini-detail" data-action="toggle-actions" title="More">
                    <i class="fa fa-ellipsis-h"></i>
                </button>
                <div class="status-mini-extra-actions">
                    <a class="status-mini-action" href="<%- ctx.formatClientLink('status', ctx.status.id) %>">
                        <i class="fa fa-external-link"></i> View thread
                    </a>
                    <% if (ctx.canEditStatus && ctx.canEditStatus(ctx.status)) { %>
                        <button class="status-mini-action" data-action="edit" title="Edit">
                            <i class="fa fa-pencil"></i> Edit
                        </button>
                    <% } %>
                    <% if (ctx.canDeleteStatus && ctx.canDeleteStatus(ctx.status)) { %>
                        <button class="status-mini-action" data-action="delete" title="Delete">
                            <i class="fa fa-trash"></i> Delete
                        </button>
                    <% } %>
                </div>
            </div>
        </div>
        <% if (!ctx.isReply) { %>
        <div class="status-mini-repost-composer" style="display:none">
            <textarea class="status-mini-repost-input" rows="2" placeholder="Add a message (optional)"></textarea>
            <div class="status-mini-repost-buttons">
                <button class="status-mini-repost-submit">Repost</button>
                <button class="status-mini-repost-cancel">Cancel</button>
            </div>
        </div>
        <% } %>
    </div>
</div>
