<div class="status-composer">
    <% if (ctx.parentStatus) { %>
        <div class="status-composer-replying">
            Replying to <a href="<%- ctx.formatClientLink('user', ctx.parentStatus.user.name) %>"><%- ctx.parentStatus.user.name %></a>
            <button class="status-composer-cancel-reply" title="Cancel reply"><i class="fa fa-times"></i></button>
        </div>
    <% } %>
    <div class="status-composer-form">
        <textarea class="status-composer-text" placeholder="What's on your mind?" maxlength="500"><%- ctx.text || '' %></textarea>
        <div class="status-composer-toolbar">
            <label class="status-composer-image-btn" title="Attach image">
                <i class="fa fa-image"></i>
                <input type="file" class="status-composer-file" accept="image/*,video/*" />
            </label>
            <% if (ctx.imagePreview) { %>
                <div class="status-composer-preview">
                    <img src="<%- ctx.imagePreview %>" alt="Preview" />
                    <button class="status-composer-remove-image" title="Remove image"><i class="fa fa-times"></i></button>
                </div>
            <% } %>
            <span class="status-composer-count"><%- ctx.text ? ctx.text.length : 0 %>/500</span>
            <button class="status-composer-submit" <%= (!ctx.text && !ctx.imagePreview) ? 'disabled' : '' %>>Post</button>
        </div>
    </div>
</div>
