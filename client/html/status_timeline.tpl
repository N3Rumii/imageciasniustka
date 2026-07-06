<div class="status-timeline-wrapper">
    <div class="messages"></div>
    <div class="status-composer-container"></div>

    <nav class="feed-tabs"><%
        %><a class="feed-tab active" data-feed="everything" href="#">Everything</a><%
        %><a class="feed-tab" data-feed="myfeed" href="#">My Feed</a><%
    %></nav>

    <nav class="sort-bar"><%
        %><span class="sort-label">Sort:</span><%
        %><button class="sort-btn sort-toggle" data-sort-base="creation-date">Date <span class="sort-dir">↓</span></button><%
        %><button class="sort-btn sort-toggle" data-sort-base="score">Likes <span class="sort-dir">↓</span></button><%
        %><button class="sort-btn sort-toggle" data-sort-base="repost-count">Reposts <span class="sort-dir">↓</span></button><%
        %><button class="sort-btn sort-clear" data-sort="">✕ clear</button><%
    %></nav>

    <div class="status-timeline">
        <div class="status-list">
            <div class="status-empty">
                <p>No statuses yet. Be the first!</p>
            </div>
        </div>
    </div>
</div>
