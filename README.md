Mastodon Post Blog
==================

Flask app for creating mastodon post for new blog entries and providing post thread ID
to blog for comment thread

## Build Container For local testing

```shell
build . -t postblog
```

## Env
```shell
MASTODON_USER = 
MASTODON_HOST = 
MASTODON_OAUTH_TOKEN =
BLOG_POST_RE = 
BLOG_POST_POSTFIX = 
BLOG_TITLE_PATTERN =
DATABASE_NAME = 
DATABASE_HOST = 
DATABASE_USER = 
DATABASE_PASSWORD = 
DATABASE_PORT = 
```

where
* `MASTODON_HOST`
  * We are assuming that the host will be accessed via `https://`
  * This is used both for the function to create the toot and returned to the caller to format client UI
* `MASTODON_USER`
  * Mastodon user under which the blog posts are created
  * This is only used to return to the caller to construct a mastodon link
* `MASTODON_OAUTH_TOKEN`
  * OAuth Token we created above to let the service post on behalf of the user
* `BLOG_POST_PATTERN`
  * Regex pattern to identify posts from referer headers
  * e.g. `^https://claassen.net/geek/blog/\d+/\d+/[^/]+` for this blog
* `BLOG_POST_POSTFIX`
  * Line to append to every post
  * e.g. common hash tags, such as `#blog`, `#iloggable`
* `BLOG_TITLE_PATTERN`
  * Regex pattern to extract `title` from `og:title` <meta>
  * e.g. the mkdocs for material blog plug-in adds the site name to each post's title in `og:title`, so I use `^(?P<title>.*?)( - claassen\.net|)$` to extract just the post title
* DATABASE_*
  * standard `USER`,`HOST`,`PASSWORD`, etc. for configuring the connection to the database

## Usage / Deployment

Refer to blog posts:

https://claassen.net/geek/blog/2024/02/mastodon-integration.html - original Lambda integration
https://claassen.net/geek/blog/2024/08/mastodon-integration-revisited.html - migration to this version

Note: You must replace `{postblog_location}` in `javascript/mastodon-loader.js` with the location of this API.
