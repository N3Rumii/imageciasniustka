<div id='user-edit'>
    <form>
        <input class='anticomplete' type='text' name='fakeuser'/>
        <input class='anticomplete' type='password' name='fakepass'/>

        <ul class='input'>
            <% if (ctx.canEditName) { %>
                <li>
                    <%= ctx.makeTextInput({
                        text: 'User name',
                        name: 'name',
                        value: ctx.user.name,
                        pattern: ctx.userNamePattern,
                    }) %>
                </li>
            <% } %>

            <% if (ctx.canEditPassword) { %>
                <li>
                    <%= ctx.makePasswordInput({
                        text: 'Password',
                        name: 'password',
                        placeholder: 'leave blank if not changing',
                        pattern: ctx.passwordPattern,
                    }) %>
                </li>
            <% } %>

            <% if (ctx.canEditEmail) { %>
                <li>
                    <%= ctx.makeEmailInput({
                        text: 'Email',
                        name: 'email',
                        value: ctx.user.email,
                    }) %>
                </li>
            <% } %>

            <% if (ctx.canEditRank) { %>
                <li>
                    <%= ctx.makeSelect({
                        text: 'Rank',
                        name: 'rank',
                        keyValues: ctx.ranks,
                        selectedKey: ctx.user.rank,
                    }) %>
                </li>
            <% } %>

            <% if (ctx.canEditAvatar) { %>
                <li class='avatar'>
                    <label>Avatar</label>
                    <div id='avatar-content'></div>
                    <div id='avatar-radio'>
                        <%= ctx.makeRadio({
                            text: 'Gravatar',
                            name: 'avatar-style',
                            value: 'gravatar',
                            selectedValue: ctx.user.avatarStyle,
                        }) %>

                        <%= ctx.makeRadio({
                            text: 'Manual avatar',
                            name: 'avatar-style',
                            value: 'manual',
                            selectedValue: ctx.user.avatarStyle,
                        }) %>
                    </div>
                </li>
            <% } %>
        </ul>

        <h2>Profile Customization</h2>
        <ul class='input'>
            <li>
                <%= ctx.makeTextarea({
                    text: 'Bio (shown under avatar, max 300 chars)',
                    name: 'profile-bio',
                    value: ctx.user.profileBio || '',
                    maxlength: '300',
                    rows: '2',
                }) %>
            </li>
            <li>
                <%= ctx.makeTextarea({
                    text: 'About (shown in sidebar, max 2000 chars)',
                    name: 'profile-about',
                    value: ctx.user.profileAbout || '',
                    maxlength: '2000',
                    rows: '3',
                }) %>
            </li>
            <li>
                <label for='profile-links'>Social Links (one per line: platform:url)</label>
                <textarea id='profile-links' name='profile-links' rows='4' maxlength='1024' placeholder='youtube:https://youtube.com/@you&#10;instagram:https://instagram.com/you&#10;twitter:https://twitter.com/you&#10;github:https://github.com/you&#10;website:https://yoursite.com'><%= ctx.user.profileLinks || '' %></textarea>
            </li>
            <li>
                <label for='profile-accent'>Accent color</label>
                <input type='color' id='profile-accent' name='profile-accent' value='<%= ctx.user.profileAccentColor || "#24aadd" %>'/>
                <div class='preset-swatches'>
                    <% var presets = ['#24aadd','#e0245e','#17bf63','#794bc4','#f5a623','#ff6b6b','#48c9b0','#e8d5b7']; %>
                    <% for (var p of presets) { %>
                        <span class='preset-swatch' style='background:<%- p %>' data-color='<%- p %>'></span>
                    <% } %>
                </div>
            </li>
            <li class='header-upload'>
                <label>Header banner (1200×300 recommended)</label>
                <div id='header-preview' style='<%= ctx.user.profileHeaderUrl ? "background-image:url(" + ctx.user.profileHeaderUrl + ")" : "" %>'></div>
                <input type='file' id='profile-header-input' accept='image/*'/>
                <button type='button' id='profile-header-upload'>Upload header</button>
            </li>
            <li>
                <%= ctx.makeSelect({
                    text: 'Feed layout',
                    name: 'profile-layout',
                    keyValues: {'list': 'List', 'masonry': 'Masonry grid'},
                    selectedKey: ctx.user.profileLayout || 'list',
                }) %>
            </li>
            <li>
                <label for='profile-embeds'>Embeds &amp; Widgets (Spotify, YouTube etc.)</label>
                <p class='css-help'>Paste iframe embed codes here. Only allowed domains: Spotify, YouTube, SoundCloud, Bandcamp, Vimeo. Others are blocked.</p>
                <textarea id='profile-embeds' name='profile-embeds' rows='4' maxlength='4096' placeholder='<iframe src="https://open.spotify.com/embed/track/..." width="300" height="80"></iframe>'><%= ctx.user.profileEmbeds || '' %></textarea>
            </li>

            <li class='css-editor-section'>
                <label>Custom CSS</label>
                <p class='css-help'>Style your profile with CSS. Your code only applies to your profile page. Put each section in its matching editor below:</p>

                <details class='css-section'>
                    <summary>🎨 Colors &amp; Background</summary>
                    <textarea class='css-area' data-css-key='colors' rows='4' maxlength='2048' placeholder='/* Page background */&#10;#user-profile { background: #ffccff; }&#10;/* Card backgrounds */&#10;#user-profile .sidebar-card,&#10;#user-profile .status-mini { background: #fff0f5; }&#10;/* Text color */&#10;#user-profile .profile-header-name { color: #333; }'></textarea>
                </details>

                <details class='css-section'>
                    <summary>🔤 Fonts &amp; Text</summary>
                    <textarea class='css-area' data-css-key='fonts' rows='4' maxlength='2048' placeholder='/* Change all fonts */&#10;#user-profile, #user-profile * { font-family: "Comic Sans MS", cursive; }&#10;/* Username size */&#10;#user-profile .profile-header-name { font-size: 2em; }'></textarea>
                </details>

                <details class='css-section'>
                    <summary>🖱️ Cursor &amp; Effects</summary>
                    <textarea class='css-area' data-css-key='effects' rows='4' maxlength='2048' placeholder='/* Custom cursor */&#10;#user-profile { cursor: url(https://cursor-url), auto; }&#10;/* Glow effect on cards */&#10;#user-profile .sidebar-card:hover { box-shadow: 0 0 15px #ff69b4; }&#10;/* Spin avatar on hover */&#10;#user-profile .profile-header-avatar:hover img { transform: rotate(360deg); transition: 0.5s; }'></textarea>
                </details>

                <details class='css-section'>
                    <summary>🎵 Widgets &amp; Extras</summary>
                    <textarea class='css-area' data-css-key='widgets' rows='4' maxlength='2048' placeholder='/* Add text before the feed */&#10;#user-profile .profile-feed::before { content: "Welcome to my blog! ♥"; display: block; text-align: center; font-size: 1.2em; padding: 10px; }&#10;/* Hide sidebar */&#10;#user-profile .profile-sidebar { display: none; }&#10;/* Make everything sparkle (gradient border) */&#10;#user-profile .profile-main { border: 3px solid transparent; border-image: linear-gradient(45deg, red, orange, yellow, green, blue, purple) 1; }'></textarea>
                </details>

                <details class='css-section'>
                    <summary>📐 Layout Tweaks</summary>
                    <textarea class='css-area' data-css-key='layout' rows='4' maxlength='2048' placeholder='/* Wider feed */&#10;#user-profile .profile-main { max-width: 800px; }&#10;/* Hide tabs */&#10;#user-profile .profile-tabs { display: none; }&#10;/* Round all corners */&#10;#user-profile .sidebar-card, #user-profile .status-mini { border-radius: 20px; }'></textarea>
                </details>

                <details class='css-section'>
                    <summary>🔥 Full Raw CSS (advanced)</summary>
                    <textarea id='profile-css' name='profile-css' rows='8' maxlength='8192' placeholder='/* Write full custom CSS here. This overrides everything above. */'><%= ctx.user.profileCss || '' %></textarea>
                </details>

                <div class='css-presets'>
                    <span class='css-preset-label'>Quick themes (fill raw CSS):</span>
                    <% var cssPresets = [
                        {name:'Vaporwave', css:'#user-profile{background:linear-gradient(180deg,#1a0033,#330066)!important}#user-profile .sidebar-card{background:rgba(255,113,206,0.15)!important}#user-profile .profile-main .status-mini{background:rgba(1,205,254,0.1)!important}#user-profile .profile-composer{background:rgba(255,113,206,0.1)!important}#user-profile .profile-composer-send{background:#ff71ce!important}#user-profile .profile-tab.active{color:#01cdfe!important;border-color:#01cdfe!important}body{font-family:"Comic Sans MS",cursive!important}'},
                        {name:'Neon', css:'#user-profile{background:#0a0a0a!important}#user-profile .sidebar-card{background:#111!important;border:1px solid #0f0!important}#user-profile .profile-main .status-mini{background:#111!important;border:1px solid #0f0!important}#user-profile .profile-composer{background:#111!important;border:1px solid #0f0!important}#user-profile .profile-composer-input{color:#0f0!important}#user-profile .profile-composer-send{background:#0f0!important;color:#000!important}#user-profile .profile-header-name{color:#0f0!important;text-shadow:0 0 10px #0f0!important}'},
                        {name:'Pastel', css:'#user-profile{background:#fff5f7!important}#user-profile .sidebar-card{background:#fff!important;border:1px solid #f8bbd0!important}#user-profile .profile-main .status-mini{background:#fff!important;border:1px solid #f8bbd0!important}#user-profile .profile-composer{background:#fff!important;border:1px solid #f8bbd0!important}#user-profile .profile-composer-send{background:#f8bbd0!important;color:#880e4f!important}#user-profile .profile-tab.active{color:#e91e63!important;border-color:#e91e63!important}#user-profile,#user-profile .profile-header-name,#user-profile .profile-composer-input{color:#880e4f!important}'},
                        {name:'Terminal', css:'#user-profile,#user-profile .sidebar-card,#user-profile .status-mini,#user-profile .profile-composer{background:#000!important;border:1px solid #0f0!important}#user-profile,#user-profile .profile-header-name,#user-profile p{color:#0f0!important;font-family:monospace!important}#user-profile .profile-composer-send{background:#0f0!important;color:#000!important}'},
                        {name:'Nature', css:'#user-profile{background:#e8f5e9!important}#user-profile .sidebar-card{background:#fff!important;border:1px solid #a5d6a7!important}#user-profile .status-mini{background:#fff!important;border:1px solid #a5d6a7!important}#user-profile .profile-composer{background:#fff!important;border:1px solid #a5d6a7!important}#user-profile .profile-composer-send{background:#66bb6a!important}#user-profile .profile-tab.active{color:#2e7d32!important;border-color:#2e7d32!important}#user-profile .profile-header-name{color:#2e7d32!important}'},
                        {name:'Retro Web', css:'body{font-family:"Comic Sans MS",cursive!important;cursor:url("data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%2232%22 height=%2232%22%3E%3Ccircle cx=%2216%22 cy=%2216%22 r=%2214%22 fill=%22%23ff0%22 stroke=%22%23f0f%22 stroke-width=%222%22/%3E%3C/svg%3E") 16 16,auto!important}#user-profile{background:url("data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%224%22 height=%224%22%3E%3Crect width=%224%22 height=%224%22 fill=%22%23000%22/%3E%3Crect width=%222%22 height=%222%22 fill=%22%23ff0%22/%3E%3C/svg%3E") #000!important}#user-profile .sidebar-card{background:rgba(255,255,0,0.1)!important;border:2px dashed #ff0!important}#user-profile .profile-header-name{color:#ff0!important;text-shadow:2px 2px #f0f!important}#user-profile .profile-composer-send{background:#ff0!important;color:#000!important}'},
                        {name:'Glitter Bomb ✨', css:'body{font-family:"Brush Script MT","Comic Sans MS",cursive!important;cursor:url("data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%2232%22 height=%2232%22%3E%3Ctext y=%2224%22 font-size=%2224%22%3E✨%3C/text%3E%3C/svg%3E") 16 16,auto!important;overflow-x:hidden!important}#user-profile{background:linear-gradient(135deg,#1a0033,#330066,#4a0080,#1a0033)!important;background-size:400% 400%!important;animation:glitter-bg 8s ease infinite!important;position:relative!important;overflow:hidden!important}#user-profile::before{content:""!important;position:fixed!important;top:0!important;left:0!important;width:100%!important;height:100%!important;pointer-events:none!important;z-index:9999!important;background-image:radial-gradient(2px 2px at 20px 30px,#fff,transparent),radial-gradient(2px 2px at 40px 70px,#ff69b4,transparent),radial-gradient(2px 2px at 50px 160px,#ffd700,transparent),radial-gradient(2px 2px at 90px 40px,#00ffff,transparent),radial-gradient(2px 2px at 130px 80px,#ff69b4,transparent),radial-gradient(2px 2px at 160px 120px,#fff,transparent),radial-gradient(3px 3px at 200px 50px,#ffd700,transparent),radial-gradient(2px 2px at 250px 100px,#00ffff,transparent),radial-gradient(3px 3px at 300px 30px,#ff69b4,transparent),radial-gradient(2px 2px at 350px 150px,#fff,transparent),radial-gradient(2px 2px at 400px 60px,#ffd700,transparent),radial-gradient(3px 3px at 450px 120px,#00ffff,transparent),radial-gradient(2px 2px at 500px 40px,#ff69b4,transparent),radial-gradient(2px 2px at 550px 90px,#fff,transparent),radial-gradient(3px 3px at 600px 140px,#ffd700,transparent),radial-gradient(2px 2px at 650px 30px,#00ffff,transparent),radial-gradient(2px 2px at 700px 100px,#ff69b4,transparent),radial-gradient(3px 3px at 750px 50px,#fff,transparent),radial-gradient(2px 2px at 800px 120px,#ffd700,transparent),radial-gradient(2px 2px at 850px 70px,#00ffff,transparent)!important;background-repeat:repeat!important;animation:glitter-sparkle 2s linear infinite!important}@keyframes glitter-bg{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}@keyframes glitter-sparkle{0%{opacity:0.6;transform:translateY(0)}50%{opacity:1;transform:translateY(-3px)}100%{opacity:0.6;transform:translateY(0)}}#user-profile .sidebar-card{background:rgba(255,255,255,0.08)!important;border:1px solid rgba(255,105,180,0.3)!important;backdrop-filter:blur(10px)!important;border-radius:16px!important;transition:all 0.3s!important}#user-profile .sidebar-card:hover{transform:scale(1.02) rotate(0.5deg)!important;box-shadow:0 0 25px rgba(255,105,180,0.4),0 0 50px rgba(255,215,0,0.2)!important;border-color:#ff69b4!important}#user-profile .profile-header-name{background:linear-gradient(90deg,#ff69b4,#ffd700,#00ffff,#ff69b4)!important;background-size:300% 100%!important;-webkit-background-clip:text!important;-webkit-text-fill-color:transparent!important;background-clip:text!important;animation:rainbow-text 3s linear infinite!important;font-size:2em!important;text-shadow:none!important}@keyframes rainbow-text{0%{background-position:0% 50%}100%{background-position:300% 50%}}#user-profile .profile-header-avatar{border-color:#ff69b4!important;box-shadow:0 0 15px rgba(255,105,180,0.5)!important;transition:all 0.3s!important;border-radius:50%!important}#user-profile .profile-header-avatar:hover{transform:rotate(10deg) scale(1.1)!important;box-shadow:0 0 30px rgba(255,215,0,0.8)!important}#user-profile .status-mini{background:rgba(255,255,255,0.05)!important;border:1px solid rgba(255,105,180,0.2)!important;border-radius:14px!important;transition:all 0.3s!important}#user-profile .status-mini:hover{background:rgba(255,105,180,0.1)!important;box-shadow:0 0 20px rgba(255,105,180,0.3)!important;transform:translateY(-2px)!important}#user-profile .profile-composer{border-color:rgba(255,105,180,0.3)!important;border-radius:14px!important}#user-profile .profile-composer-send{background:linear-gradient(135deg,#ff69b4,#ffd700)!important;border-radius:20px!important;font-weight:700!important;animation:pulse-btn 2s ease infinite!important}@keyframes pulse-btn{0%,100%{box-shadow:0 0 5px rgba(255,105,180,0.5)}50%{box-shadow:0 0 20px rgba(255,215,0,0.8),0 0 30px rgba(255,105,180,0.4)}}#user-profile .profile-tab{transition:all 0.3s!important}#user-profile .profile-tab:hover{color:#ff69b4!important;text-shadow:0 0 8px rgba(255,105,180,0.5)!important}#user-profile .profile-tab.active{color:#ffd700!important;border-color:#ffd700!important;text-shadow:0 0 10px rgba(255,215,0,0.6)!important}#user-profile .profile-stats span{transition:all 0.2s!important}#user-profile .profile-stats span:hover{transform:scale(1.1)!important;text-shadow:0 0 10px rgba(255,255,255,0.5)!important}#user-profile .profile-follow-btn.follow{background:linear-gradient(135deg,#ff69b4,#ff1493)!important;border:none!important}#user-profile .profile-customize-btn{border-color:#ffd700!important;color:#ffd700!important;text-shadow:0 0 5px rgba(255,215,0,0.3)!important}'},
                    ]; %>
                    <% for (var cp of cssPresets) { %>
                        <button type='button' class='css-preset-btn' data-css='<%- cp.css %>'><%- cp.name %></button>
                    <% } %>
                </div>
            </li>
        </ul>

        <div class='messages'></div>

        <div class='buttons'>
            <input type='submit' value='Save settings'/>
        </div>
    </form>
</div>
