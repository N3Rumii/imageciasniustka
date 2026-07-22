<div id="user-profile">
    <% var accent = ctx.profileAccentColor || '#1da1f2'; %>

    <!-- Two-column layout -->
    <div class="profile-layout">

        <!-- ============ LEFT COLUMN: Feed ============ -->
        <main class="profile-main">

            <!-- Sub-navigation tabs -->
            <nav class="profile-tabs">
                <a class="profile-tab active" data-tab="blog">Blog Posts</a>
                <a class="profile-tab" data-tab="media">Media</a>
                <a class="profile-tab" data-tab="statuses">Community Posts</a>
            </nav>

            <!-- Blog post composer (own profile only) -->
            <% if (ctx.isOwnProfile) { %>
            <div class="profile-composer">
                <textarea class="profile-composer-input" rows="2" placeholder="Write a blog post..." maxlength="3000"></textarea>
                <div class="profile-composer-actions">
                    <span class="profile-composer-count">0 / 3000</span>
                    <label class="profile-composer-attach">
                        <i class="fa fa-image"></i>
                        <input type="file" class="profile-composer-file" accept="image/*,video/*"/>
                    </label>
                    <button class="profile-composer-send">Post</button>
                </div>
            </div>
            <% } %>

            <!-- Feed -->
            <div class="profile-feed">
                <div class="profile-feed-empty">
                    <p>No posts yet.</p>
                </div>
            </div>


        </main>

        <!-- ============ RIGHT COLUMN: Sidebar ============ -->
        <aside class="profile-sidebar">

            <!-- Header card -->
            <div class="sidebar-card profile-header-card">
                <div class="profile-header-bg" style="<%= ctx.profileHeaderUrl ? 'background-image:url(' + ctx.profileHeaderUrl + ')' : 'background:' + accent %>"></div>
                <div class="profile-header-avatar">
                    <img src="<%- ctx.user.avatarUrl %>" alt="<%- ctx.user.name %>"/>
                </div>
                <h2 class="profile-header-name"><%- ctx.user.name %></h2>
                <% if (ctx.user.profileBio) { %>
                    <p class="profile-header-bio"><%= ctx.user.profileBio %></p>
                <% } %>
                <div class="profile-header-stats">
                    <span><strong><%- ctx.user.uploadedPostCount %></strong> posts</span>
                    <span><strong><%- ctx.user.followersCount %></strong> followers</span>
                    <span><strong><%- ctx.user.followingCount %></strong> following</span>
                </div>
                <div class="profile-header-actions">
                    <% if (ctx.isOwnProfile) { %>
                        <a class="sidebar-btn customize-btn" href="<%- ctx.formatClientLink('user', ctx.user.name, 'edit') %>">Customize</a>
                    <% } else { %>
                        <button class="sidebar-btn follow-btn <%= ctx.user.isFollowing ? 'unfollow' : 'follow' %>">
                            <%= ctx.user.isFollowing ? 'Unfollow' : 'Follow' %>
                        </button>
                        <button class="sidebar-btn block-btn <%= ctx.user.isBlocked ? 'unblock' : 'block' %>">
                            <%= ctx.user.isBlocked ? 'Unblock' : 'Block' %>
                        </button>
                    <% } %>
                </div>
            </div>

            <!-- About card -->
            <div class="sidebar-card">
                <h3>About</h3>
                <p>Joined <%= ctx.makeRelativeTime(ctx.user.creationTime) %></p>
                <% if (ctx.user.profileAbout) { %>
                    <p class="profile-about-text"><%= ctx.user.profileAbout %></p>
                <% } else { %>
                    <p class="profile-about-empty">Nothing here yet.</p>
                <% } %>
            </div>

            <!-- Social Links card -->
            <% if (ctx.user.profileLinks) { %>
            <div class="sidebar-card">
                <h3>Links</h3>
                <div class="profile-social-links">
                    <% var links = ctx.user.profileLinks.split('\n'); %>
                    <% for (var l of links) { %>
                        <% var parts = l.split(':'); var platform = parts[0]; var url = parts.slice(1).join(':'); %>
                        <a class="social-link social-<%= platform %>" href="<%= url %>" target="_blank" rel="noopener">
                            <i class="fa fa-<%= {youtube:'youtube-play', instagram:'instagram', twitter:'twitter', github:'github', facebook:'facebook', website:'globe', discord:'comments', twitch:'twitch', spotify:'spotify', tiktok:'music', reddit:'reddit'}[platform] || 'link' %>"></i>
                            <span><%= platform.charAt(0).toUpperCase() + platform.slice(1) %></span>
                        </a>
                    <% } %>
                </div>
            </div>
            <% } %>

            <!-- Embeds card -->
            <% if (ctx.user.profileEmbeds) { %>
            <div class="sidebar-card profile-embeds-card">
                <h3>🎵</h3>
                <div class="profile-embeds-content"><%= ctx.user.profileEmbeds %></div>
            </div>
            <% } %>

            <!-- Links card -->
            <div class="sidebar-card">
                <h3>Browse</h3>
                <a href="<%- ctx.formatClientLink('posts', {query:'submit:'+ctx.user.name}) %>">Uploads</a>
                <a href="<%- ctx.formatClientLink('posts', {query:'fav:'+ctx.user.name}) %>">Favorites</a>
                <a href="<%- ctx.formatClientLink('timeline', {query:'user:'+ctx.user.name}) %>">Timeline</a>
            </div>
        </aside>
    </div>
</div>