<div class='content-wrapper transparent' id='home'>
    <div class='messages'></div>
    <header>
        <h1><%- ctx.name %></h1>
    </header>
    <div class='home-community-cta'>
        <a class='home-community-btn' href='<%- ctx.formatClientLink('timeline') %>'>Visit Community</a>
        <span class='home-cta-sub'>or check media:</span>
    </div>
    <% if (ctx.canListPosts) { %>
        <form class='horizontal'>
            <%= ctx.makeTextInput({name: 'search-text', placeholder: 'enter some tags'}) %>
            <input type='submit' value='Search'/>
            <span class=sep>or</span>
            <a href='<%- ctx.formatClientLink('posts') %>'>browse all media</a>
        </form>
    <% } %>
    <div class='post-info-container'></div>
    <footer class='footer-container'></footer>
</div>
