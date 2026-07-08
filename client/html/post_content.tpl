<div class='post-content post-type-<%- ctx.post.type %>'>
    <% if (['image', 'animation'].includes(ctx.post.type)) { %>

        <img class='resize-listener' alt='' src='<%- ctx.post.contentUrl %>'/>

    <% } else if (ctx.post.type === 'flash') { %>

        <object class='resize-listener' width='<%- ctx.post.canvasWidth %>' height='<%- ctx.post.canvasHeight %>' data='<%- ctx.post.contentUrl %>'>
            <param name='wmode' value='opaque'/>
            <param name='movie' value='<%- ctx.post.contentUrl %>'/>
        </object>

    <% } else if (ctx.post.type === 'video') { %>

        <%= ctx.makeElement(
            'video', {
                class: 'resize-listener',
                controls: true,
                loop: (ctx.post.flags || []).includes('loop'),
                playsinline: true,
                autoplay: ctx.autoplay,
            },
            ctx.makeElement('source', {
                type: ctx.post.mimeType,
                src: ctx.post.contentUrl,
            }),
            'Your browser doesn\'t support HTML5 videos.')
        %>

    <% } else if (ctx.post.type === 'audio') { %>

        <div class='music-player resize-listener'>
            <div class='music-player-artwork'>
                <img src='<%- ctx.post.thumbnailUrl || "" %>' alt='Cover' onerror="this.style.display='none';this.nextElementSibling.style.display='flex'"/>
                <div class='music-player-artwork-fallback' style='display:none'><i class='fa fa-music'></i></div>
            </div>
            <div class='music-player-main'>
                <div class='music-player-info'>
                    <span class='music-player-title'><%- (ctx.post.tags && ctx.post.tags.length ? ctx.post.tags[0].names[0] : 'Untitled') %></span>
                    <span class='music-player-artist'><%- ctx.post.user ? ctx.post.user.name : 'Unknown' %></span>
                </div>
                <audio controls preload='auto' src='<%- ctx.post.contentUrl %>' type='audio/opus' style='width:100%;max-width:500px'></audio>
                <a class='music-player-download' href='<%- ctx.post.contentUrl %>' download><i class='fa fa-download'></i> Download</a>
            </div>
        </div>

    <% } else { console.log(new Error('Unknown post type')); } %>

    <div class='post-overlay resize-listener'>
    </div>
</div>
