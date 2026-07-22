<div class='community-page'>
    <div class='status-composer-container'></div>

    <nav class='feed-tabs'><%
        %><a class='feed-tab <%- (ctx.parameters.feed || "everything") === "everything" ? "active" : "" %>' data-feed='everything' href='#'>Everything</a><%
        %><a class='feed-tab <%- ctx.parameters.feed === "myfeed" ? "active" : "" %>' data-feed='myfeed' href='#'>My Feed</a><%
    %></nav>

    <nav class='sort-bar'><%
        %><span class='sort-label'>Sort:</span><%
        %><button class='sort-btn <%- ctx.parameters.sort === "creation-date" ? "active" : "" %>' data-sort='creation-date'>Date ↓</button><%
        %><button class='sort-btn <%- ctx.parameters.sort === "creation-date,asc" ? "active" : "" %>' data-sort='creation-date,asc'>Date ↑</button><%
        %><button class='sort-btn <%- ctx.parameters.sort === "score" ? "active" : "" %>' data-sort='score'>Likes ↓</button><%
        %><button class='sort-btn <%- ctx.parameters.sort === "score,asc" ? "active" : "" %>' data-sort='score,asc'>Likes ↑</button><%
        %><button class='sort-btn <%- ctx.parameters.sort === "repost-count" ? "active" : "" %>' data-sort='repost-count'>Reposts ↓</button><%
        %><button class='sort-btn <%- ctx.parameters.sort === "repost-count,asc" ? "active" : "" %>' data-sort='repost-count,asc'>Reposts ↑</button><%
        %><button class='sort-btn <%- ctx.parameters.sort === "fav-count" ? "active" : "" %>' data-sort='fav-count'>Favs ↓</button><%
        %><button class='sort-btn <%- ctx.parameters.sort === "fav-count,asc" ? "active" : "" %>' data-sort='fav-count,asc'>Favs ↑</button><%
        %><% if (ctx.parameters.sort) { %><%
            %><button class='sort-btn sort-clear' data-sort=''>✕ clear</button><%
        %><% } %><%
    %></nav>

    <div class='community-messages'></div>
    <div class='community-post-grid'></div>
    <div class='community-pager'></div>
</div>
