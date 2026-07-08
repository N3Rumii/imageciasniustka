<nav id='notifications-page' class='content-wrapper'>
    <div class='page-header'>
        <h1>Notifications</h1>
        <div class='notification-actions'>
            <% if (ctx.notifications.length) { %>
                <button class='mark-all-read'>Mark all read</button>
                <button class='dismiss-all'>Dismiss all</button>
            <% } %>
        </div>
    </div>
    <ul class='notification-list'>
        <% if (!ctx.notifications.length) { %>
            <li class='empty'>No notifications yet.</li>
        <% } %>
        <% for (let n of ctx.notifications) { %>
            <li class='notification-item <%= n.isRead ? "" : "unread" %>' data-id='<%- n.id %>'>
                <div class='notification-icon'>
                    <i class='fa <%- ctx.getIcon(n.type) %>'></i>
                </div>
                <div class='notification-content'>
                    <% if (n.actor) { %>
                        <a href='/user/<%- n.actor.name %>' class='actor'>
                            <%- n.actor.name %>
                        </a>
                    <% } %>
                    <span class='action'><%- ctx.getLabel(n.type) %></span>
                    <% if (n.groupCount > 1) { %>
                        <span class='group-count'>×<%- n.groupCount %></span>
                    <% } %>
                    <% if (n.comment && n.comment.text) { %>
                        <span class='comment-preview'>"<%- n.comment.text.slice(0, 100) %>"</span>
                    <% } %>
                    <span class='time'><%- ctx.formatTime(n.creationTime) %></span>
                </div>
                <div class='notification-actions'>
                    <% if (!n.isRead) { %>
                        <button class='mark-read' title='Mark as read'>
                            <i class='fa fa-check'></i>
                        </button>
                    <% } %>
                    <button class='dismiss' title='Dismiss'>
                        <i class='fa fa-times'></i>
                    </button>
                </div>
            </li>
        <% } %>
    </ul>
</nav>
