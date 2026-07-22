<div class='gallery-merge'>
    <form>
        <ul class='input'>
            <li class='target'>
                <%= ctx.makeTextInput({name: 'target-gallery', required: true, text: 'Target gallery', pattern: ctx.poolNamePattern}) %>
            </li>

            <li>
                <p>Posts in the two galleries will be combined.
                Category needs to be handled manually.</p>

                <%= ctx.makeCheckbox({required: true, text: 'I confirm that I want to merge this gallery.'}) %>
            </li>
        </ul>

        <div class='messages'></div>

        <div class='buttons'>
            <input type='submit' value='Merge gallery'/>
        </div>
    </form>
</div>
