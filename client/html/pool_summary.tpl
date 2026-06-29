<div class='content-wrapper gallery-summary'>
    <section class='details'>
        <section>
            Category:
            <span class='<%= ctx.makeCssName(ctx.pool.category, 'gallery') %>'><%- ctx.pool.category %></span>
        </section>

        <section>
        Aliases:<br/>
        <ul><!--
            --><% for (let name of ctx.pool.names.slice(1)) { %><!--
                --><li><%= ctx.makeGalleryLink(ctx.pool.id, false, false, ctx.pool, name) %></li><!--
            --><% } %><!--
        --></ul>
        </section>
    </section>

    <% if (ctx.pool.isPrivate) { %>
        <section class='private-info'>
            <i class='fa fa-lock'></i> Private gallery
        </section>
    <% } %>

    <section class='description'>
        <hr/>
        <%= ctx.makeMarkdown(ctx.pool.description || 'This gallery has no description yet.') %>
        <p>This gallery has <a href='<%- ctx.formatClientLink('posts', {query: 'pool:' + ctx.pool.id}) %>'><%- ctx.pool.postCount %> post(s)</a>.</p>
    </section>

    <% if (ctx.pool.posts && ctx.pool.posts.length) { %>
        <section class='gallery-posts'>
            <div class='thumbnail-grid'>
                <% for (let post of ctx.pool.posts) { %>
                    <a href='<%- ctx.formatClientLink('post', post.id) %>' class='thumbnail-item'>
                        <img src='<%- post.thumbnailUrl %>' alt='' loading='lazy'/>
                    </a>
                <% } %>
            </div>
        </section>
    <% } %>
</div>
