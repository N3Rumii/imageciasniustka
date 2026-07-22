<p>Customize your profile with your own CSS! Go to your profile → <strong>Customize</strong> → scroll to the <strong>Custom CSS</strong> section. Your CSS only affects your profile page, not the rest of the site.</p>

<p class='section'><strong>Selectors you can target</strong></p>
<table>
    <tbody>
        <tr><td><code>#user-profile</code></td><td>The whole profile page</td></tr>
        <tr><td><code>.profile-header-card</code></td><td>Your avatar and name card in the sidebar</td></tr>
        <tr><td><code>.profile-header-bg</code></td><td>The colored bar behind your avatar</td></tr>
        <tr><td><code>.profile-header-name</code></td><td>Your username text</td></tr>
        <tr><td><code>.profile-header-avatar</code></td><td>Your avatar image container</td></tr>
        <tr><td><code>.sidebar-card</code></td><td>Any card in the sidebar</td></tr>
        <tr><td><code>.profile-main</code></td><td>The main feed column</td></tr>
        <tr><td><code>.profile-composer</code></td><td>The blog post writing box</td></tr>
        <tr><td><code>.profile-composer-send</code></td><td>The Post button</td></tr>
        <tr><td><code>.profile-tab.active</code></td><td>The active tab underline</td></tr>
        <tr><td><code>.status-mini</code></td><td>Individual post cards</td></tr>
        <tr><td><code>.profile-feed-empty</code></td><td>The "no posts yet" message</td></tr>
    </tbody>
</table>

<p class='section'><strong>Examples</strong></p>
<table>
    <tbody>
        <tr><td><code>background: #ffccff;</code></td><td>Change background color</td></tr>
        <tr><td><code>background: url(https://...);</code></td><td>Use an image as background</td></tr>
        <tr><td><code>font-family: "Comic Sans MS";</code></td><td>Change font</td></tr>
        <tr><td><code>cursor: url(...), auto;</code></td><td>Custom cursor</td></tr>
        <tr><td><code>border-radius: 20px;</code></td><td>Round corners</td></tr>
        <tr><td><code>box-shadow: 0 0 15px pink;</code></td><td>Glow effect</td></tr>
        <tr><td><code>display: none;</code></td><td>Hide an element</td></tr>
        <tr><td><code>transform: rotate(5deg);</code></td><td>Tilt an element</td></tr>
        <tr><td><code>::before { content: "♥"; }</code></td><td>Add text before something</td></tr>
    </tbody>
</table>

<p class='section'><strong>Restrictions</strong></p>
<ul>
    <li>Max 8 KB total CSS</li>
    <li><code>url()</code>, <code>@import</code>, and <code>javascript:</code> are blocked for safety</li>
    <li>CSS only applies to your profile page — it won't affect the timeline, posts, or other users' pages</li>
    <li>If you break your profile, you can always reset it from the Customize page</li>
</ul>