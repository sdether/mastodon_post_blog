import hashlib
import logging
import os
import re
from html.parser import HTMLParser
from typing import Optional

import psycopg2
import requests
from psycopg2.extras import RealDictCursor
from flask import Flask, request
from logging.config import dictConfig

dictConfig({
    'version': 1,
    "formatters": {
        "verbose": {
            "format": "[{levelname}] {module} {message}",
            "style": "{",
        },
        "simple": {
            "format": "[{levelname}] {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose"
        },
    },
    'loggers': {
        'urllib3': {
            "handlers": ["console"],
            "level": 'WARNING',
            'propagate': False
        },
        'requests': {
            "handlers": ["console"],
            "level": 'WARNING',
            'propagate': False
        },
    },
    'root': {
        'level': 'DEBUG',
        'handlers': ['console']
    }
})

logger = logging.getLogger(__name__)


class BadRequest(Exception):
    pass


MASTODON_USER = os.environ['MASTODON_USER']
MASTODON_HOST = os.environ['MASTODON_HOST']
MASTODON_OAUTH_TOKEN = os.environ['MASTODON_OAUTH_TOKEN']
BLOG_POST_RE = re.compile(os.environ['BLOG_POST_PATTERN'])
BLOG_POST_POSTFIX = os.environ.get('BLOG_POST_POSTFIX')
BLOG_TITLE_PATTERN = os.environ.get('BLOG_TITLE_PATTERN')
DATABASE_NAME = os.environ['DATABASE_NAME']
DATABASE_HOST = os.environ['DATABASE_HOST']
DATABASE_USER = os.environ['DATABASE_USER']
DATABASE_PASSWORD = os.environ['DATABASE_PASSWORD']
DATABASE_PORT = os.environ.get('DATABASE_PORT', 5432)

if BLOG_TITLE_PATTERN:
    BLOG_TITLE_RE = re.compile(BLOG_TITLE_PATTERN)
else:
    BLOG_TITLE_RE = None

app = Flask(__name__)
application = app

with app.app_context():
    for env_name in ['BLOG_POST_PATTERN', 'BLOG_POST_POSTFIX', 'MASTODON_USER',
                     'MASTODON_HOST', 'DATABASE_NAME']:
        logger.debug(f"VAR:{env_name}: {os.environ[env_name]}")


@app.route('/status')
def status():
    return dict(code=200, message='OK', rev=os.environ['VERSION'])


@app.route('/')
def postblog():
    url = None
    try:
        url = request.args.get('url')
        if not url:
            raise BadRequest("No `url` query argument provided")
        if not BLOG_POST_RE.match(url):
            logger.debug(f"url `{url}` is not handled")
            raise BadRequest("Provided `url` is not a handled")
        logger.debug(f"invoked for {url}")
        toot_id = get_toot_id(url)
        logger.info(f"resolved {url} to toot_id {toot_id}")
        return (
            dict(host=MASTODON_HOST,
                 user=MASTODON_USER,
                 toot_id=str(toot_id)),
            200,
            {'Access-Control-Allow-Origin': '*'}
        )
    except BadRequest as e:
        return (
            dict(code=400, error=e.args[0]),
            400,
            {'Access-Control-Allow-Origin': '*'}
        )
    except Exception:
        logger.exception(f"request for {url} failed")
        raise


def get_toot_id(url):
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, toot_id FROM posts WHERE url = %s FOR SHARE", (url,))
        row = cur.fetchone()
        toot_id = row.get('toot_id') if row else None
        if toot_id:
            return toot_id
        if not row:
            cur.execute("INSERT into posts (url) VALUES(%s) ON CONFLICT DO NOTHING", (url,))
        cur.execute("SELECT id, toot_id FROM posts WHERE url = %s FOR UPDATE", (url,))
        row = cur.fetchone()
        toot_id = row['toot_id']
        if toot_id:
            return toot_id
        post_id = row['id']
        toot_id = create_toot(url, post_id)
        cur.execute("UPDATE posts SET toot_id = %s WHERE id = %s", (toot_id, post_id))
        return toot_id


def create_toot(url, post_id):
    logger.debug(f"creating toot for post_id {post_id}/{url}")
    response = requests.get(url)
    if response.status_code != 200:
        raise BadRequest("Post does not exist yet")
    parser = HTMLMetaParser()
    parser.feed(response.text)
    parser.close()
    title = parser.meta.get('og:title')
    if title and BLOG_TITLE_RE:
        m = BLOG_TITLE_RE.match(title)
        if m:
            title = m.group('title')
    description = parser.meta.get('og:description')
    status = ""
    if title:
        status = f"{title}\n\n"
    if description:
        status += f"{description}\n"
    if BLOG_POST_POSTFIX:
        status += f"{BLOG_POST_POSTFIX}\n"
    status += url
    status_url = f"https://{MASTODON_HOST}/api/v1/statuses"
    response = requests.post(status_url,
                             headers={"Authorization": f"Bearer {MASTODON_OAUTH_TOKEN}",
                                      "Idempotency-Key": md5(url)},
                             data=dict(status=status))
    if response.status_code != 200:
        raise Exception(
            f"Toot creation via {status_url} failed: [{response.status_code}] {response.text}"
        )
    return int(response.json()['id'])


def md5(data):
    m = hashlib.md5()
    m.update(data.encode('utf-8'))
    return m.hexdigest()


def get_db_connection():
    return psycopg2.connect(dbname=DATABASE_NAME,
                            user=DATABASE_USER,
                            password=DATABASE_PASSWORD,
                            host=DATABASE_HOST,
                            port=DATABASE_PORT)


class HTMLMetaParser(HTMLParser):

    def __init__(self, *args, **kwargs):
        self.in_head = False
        self.meta = {}
        super().__init__(*args, **kwargs)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if self.in_head and tag == 'meta':
            prop, content = None, None
            for k, v in attrs:
                if k == 'property':
                    prop = v
                if k == 'content':
                    content = v
            if prop:
                self.meta[prop] = content
        elif tag == 'head':
            self.in_head = True

    def handle_endtag(self, tag: str) -> None:
        if self.in_head and tag == 'head':
            self.in_head = False
