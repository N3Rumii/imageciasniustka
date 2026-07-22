<div class='gallery-list-header'>
    <form class='horizontal'>
        <ul class='input'>
            <li>
                <%= ctx.makeTextInput({text: 'Search query', id: 'search-text', name: 'search-text', value: ctx.parameters.query}) %>
            </li>
        </ul>

        <div class='buttons'>
            <input type='submit' value='Search'/>
            <a class='button append' href='<%- ctx.formatClientLink('help', 'search', 'pools') %>'>Syntax help</a>

            <% if (ctx.canCreate) { %>
                <a class='append' href='<%- ctx.formatClientLink('pool', 'create') %>'>Add new gallery</a>
            <% } %>

            <% if (ctx.canEditGalleryCategories) { %>
                <a class='append' href='<%- ctx.formatClientLink('pool-categories') %>'>Gallery categories</a>
            <% } %>
        </div>
    </form>
</div>
