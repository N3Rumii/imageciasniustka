<div id='post-upload'>
    <form>
        <div class='dropper-container'></div>

        <div class='control-strip'>
            <input type='submit' value='Upload all' class='submit'/>

            <span class='skip-duplicates'>
                <%= ctx.makeCheckbox({
                    text: 'Skip duplicate',
                    name: 'skip-duplicates',
                    checked: false,
                }) %>
            </span>

            <span class='always-upload-similar'>
                <%= ctx.makeCheckbox({
                    text: 'Force upload similar',
                    name: 'always-upload-similar',
                    checked: false,
                }) %>
            </span>

            <span class='pause-remain-on-error'>
                <%= ctx.makeCheckbox({
                    text: 'Pause on error',
                    name: 'pause-remain-on-error',
                    checked: true,
                }) %>
            </span>

            <span class='private-post'>
                <%= ctx.makeCheckbox({
                    text: 'Private (only you and whitelisted users can view)',
                    name: 'private-post',
                    checked: false,
                }) %>
            </span>

            <span class='whitelist-input' style='display:none'>
                <label>Whitelist (comma-separated usernames):</label>
                <input type='text' name='whitelist' placeholder='user1, user2, ...' class='whitelist'/>
            </span>

            <input type='button' value='Cancel' class='cancel'/>
        </div>

        <div class='messages'></div>

        <ul class='uploadables-container'></ul>
    </form>
</div>
