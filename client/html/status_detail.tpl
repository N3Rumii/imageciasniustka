<div class="status-detail-wrapper">
    <div class="messages"></div>
    <div class="status-detail">
        <a class="status-detail-back" href="<%- ctx.formatClientLink('timeline') %>">
            <i class="fa fa-arrow-left"></i> Back to timeline
        </a>
        <div class="status-detail-main">
            <%= ctx.renderStatusMini(ctx.status) %>
        </div>
        <div class="status-detail-replies">
            <h3>Replies</h3>
            <% if (ctx.replies && ctx.replies.length) { %>
                <% for (let reply of ctx.replies) { %>
                    <%= ctx.renderStatusMini(reply) %>
                <% } %>
            <% } else { %>
                <p class="status-detail-no-replies">No replies yet.</p>
            <% } %>
        </div>
        <div class="status-composer-container"></div>
    </div>
</div>
