document$.subscribe(function () {
    let c = document.getElementById('comments');
    if (c) {
        let url = new URL(document.URL);
        url.search = '';
        url.username = '';
        url.password = '';
        url.hash = '';
        fetch('{postblog_location}/?url=' + encodeURIComponent(url.href))
            .then((response) => response.json())
            .then((data) => {
                if(data['toot_id'] > 0) {
                    c.innerHTML = '<mastodon-comments host="'
                        + data['host']
                        + '" user="'
                        + data['user']
                        + '" tootId="'
                        + data['toot_id']
                        + '" ></mastodon-comments>';
                }
            });
    }
});
