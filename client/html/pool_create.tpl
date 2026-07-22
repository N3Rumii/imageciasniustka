<div class='content-wrapper gallery-create'>
    <form>
        <ul class='input'>
            <li class='names'>
                <%= ctx.makeTextInput({
                    text: 'Names',
                    value: '',
                    required: true,
                }) %>
            </li>
            <li class='category'>
                <%= ctx.makeSelect({
                    text: 'Category',
                    keyValues: ctx.categories,
                    selectedKey: 'default',
                    required: true,
                }) %>
            </li>
            <li class='description'>
                <%= ctx.makeTextarea({
                    text: 'Description',
                    value: '',
                }) %>
            </li>
            <li class='posts'>
                <%= ctx.makeTextInput({
                    text: 'Posts',
                    value: '',
                    placeholder: 'space-separated post IDs',
                }) %>
            </li>
            <li class='private-gallery'>
                <%= ctx.makeCheckbox({
                    text: 'Private gallery',
                    name: 'private-gallery',
                    checked: false,
                }) %>
            </li>
            <li class='whitelist-input' style='display:none'>
                <label>Whitelist usernames (comma-separated):</label>
                <input type='text' name='whitelist' placeholder='user1, user2'/>
            </li>
        </ul>

        <% if (ctx.canCreate) { %>
            <div class='messages'></div>

            <div class='buttons'>
                <input type='submit' class='save' value='Create gallery'>
            </div>
        <% } %>
    </form>
</div>
