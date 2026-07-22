<div class='gallery-list table-wrap'>
    <% if (ctx.response.results.length) { %>
        <table>
            <thead>
                <th class='names'>
                    <% if (ctx.parameters.query == 'sort:name' || !ctx.parameters.query) { %>
                        <a href='<%- ctx.formatClientLink('pools', {query: '-sort:name'}) %>'>Gallery name(s)</a>
                    <% } else { %>
                        <a href='<%- ctx.formatClientLink('pools', {query: 'sort:name'}) %>'>Gallery name(s)</a>
                    <% } %>
                </th>
                <th class='post-count'>
                     <% if (ctx.parameters.query == 'sort:post-count') { %>
                        <a href='<%- ctx.formatClientLink('pools', {query: '-sort:post-count'}) %>'>Post count</a>
                     <% } else { %>
                        <a href='<%- ctx.formatClientLink('pools', {query: 'sort:post-count'}) %>'>Post count</a>
                     <% } %>
                     </th>
                <th class='creation-time'>
                    <% if (ctx.parameters.query == 'sort:creation-time') { %>
                        <a href='<%- ctx.formatClientLink('pools', {query: '-sort:creation-time'}) %>'>Created on</a>
                    <% } else { %>
                        <a href='<%- ctx.formatClientLink('pools', {query: 'sort:creation-time'}) %>'>Created on</a>
                    <% } %>
                </th>
            </thead>
            <tbody>
                <% for (let gallery of ctx.response.results) { %>
                    <tr>
                        <td class='names'>
                            <ul>
                                <% for (let name of gallery.names) { %>
                                    <li><%= ctx.makePoolLink(gallery.id, false, false, gallery, name) %></li>
                                <% } %>
                            </ul>
                        </td>
                        <td class='post-count'>
                            <a href='<%- ctx.formatClientLink('posts', {query: 'pool:' + gallery.id}) %>'><%- gallery.postCount %></a>
                        </td>
                        <td class='creation-time'>
                            <%= ctx.makeRelativeTime(gallery.creationTime) %>
                        </td>
                    </tr>
                <% } %>
            </tbody>
        </table>
    <% } %>
</div>
