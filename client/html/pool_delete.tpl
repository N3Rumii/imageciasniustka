<div class='gallery-delete'>
    <form>
        <p>This gallery has <a href='<%- ctx.formatClientLink('posts', {query: 'pool:' + ctx.pool.id}) %>'><%- ctx.pool.postCount %> post(s)</a>.</p>

        <ul class='input'>
            <li>
                <%= ctx.makeCheckbox({
                    name: 'confirm-deletion',
                    text: 'I confirm that I want to delete this gallery.',
                    required: true,
                }) %>
            </li>
        </ul>

        <div class='messages'></div>

        <div class='buttons'>
            <input type='submit' value='Delete gallery'/>
        </div>
    </form>
</div>
