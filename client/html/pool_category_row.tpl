<% if (ctx.poolCategory.isDefault) { %><%
    %><tr data-category='<%- ctx.poolCategory.name %>' class='default'><%
%><% } else { %><%
    %><tr data-category='<%- ctx.poolCategory.name %>'><%
%><% } %>
    <td class='name'>
        <% if (ctx.canEditName) { %>
            <%= ctx.makeTextInput({value: ctx.poolCategory.name, required: true}) %>
        <% } else { %>
            <%- ctx.poolCategory.name %>
        <% } %>
    </td>
    <td class='color'>
        <% if (ctx.canEditColor) { %>
            <%= ctx.makeColorInput({value: ctx.poolCategory.color}) %>
        <% } else { %>
            <%- ctx.poolCategory.color %>
        <% } %>
    </td>
    <td class='usages'>
        <% if (ctx.poolCategory.name) { %>
            <a href='<%- ctx.formatClientLink('pools', {query: 'category:' + ctx.poolCategory.name}) %>'>
                <%- ctx.poolCategory.galleryCount %>
            </a>
        <% } else { %>
            <%- ctx.poolCategory.galleryCount %>
        <% } %>
    </td>
    <% if (ctx.canDelete) { %>
        <td class='remove'>
            <% if (ctx.poolCategory.galleryCount) { %>
                <a class='inactive' title="Can't delete category in use">Remove</a>
            <% } else { %>
                <a href>Remove</a>
            <% } %>
        </td>
    <% } %>
    <% if (ctx.canSetDefault) { %>
        <td class='set-default'>
            <a href>Make default</a>
        </td>
    <% } %>
</tr>
