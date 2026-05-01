import hashlib
import logging
import os
import re
from html.parser import HTMLParser
from typing import Optional
from urllib.parse import urlparse

import boto3
import requests
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class BadRequest(Exception):
    pass


MASTODON_USER = os.environ.get('MASTODON_USER', '')
MASTODON_HOST = os.environ.get('MASTODON_HOST', '')
MASTODON_OAUTH_TOKEN = os.environ.get('MASTODON_OAUTH_TOKEN')
_blog_post_pattern = os.environ.get('BLOG_POST_PATTERN')
BLOG_POST_RE = re.compile(_blog_post_pattern) if _blog_post_pattern else None
BLOG_POST_POSTFIX = os.environ.get('BLOG_POST_POSTFIX')
BLOG_TITLE_PATTERN = os.environ.get('BLOG_TITLE_PATTERN')
S3_KEY = os.environ.get('S3_KEY')
S3_SECRET = os.environ.get('S3_SECRET')
S3_ENDPOINT = os.environ.get('S3_ENDPOINT')
S3_BUCKET = os.environ.get('S3_BUCKET')

if BLOG_TITLE_PATTERN:
    BLOG_TITLE_RE = re.compile(BLOG_TITLE_PATTERN)
else:
    BLOG_TITLE_RE = None

for env_name in ['BLOG_POST_PATTERN', 'BLOG_POST_POSTFIX', 'MASTODON_USER', 'MASTODON_HOST', 'S3_BUCKET']:
    logger.debug(f"VAR:{env_name}: {os.environ.get(env_name)}")

_s3 = None


def _get_s3():
    global _s3
    if _s3 is None:
        kwargs = {}
        if S3_ENDPOINT:
            kwargs['endpoint_url'] = S3_ENDPOINT
        if S3_KEY:
            kwargs['aws_access_key_id'] = S3_KEY
        if S3_SECRET:
            kwargs['aws_secret_access_key'] = S3_SECRET
        _s3 = boto3.client('s3', **kwargs)
    return _s3


def get_s3_key(url):
    parsed = urlparse(url)
    return f'.mastodon-meta/{parsed.path.lstrip("/")}'


def build_status(url) -> str:
    """Fetch url and build the Mastodon status text."""
    response = requests.get(url)
    if response.status_code != 200:
        raise BadRequest("Post does not exist yet")
    parser = HTMLMetaParser()
    parser.feed(response.text)
    parser.close()
    title = parser.meta.get('mastodon:title')
    if not title:
        title = parser.meta.get('og:title') or parser.meta.get('twitter:title')
        if title and BLOG_TITLE_RE:
            m = BLOG_TITLE_RE.match(title)
            if m:
                title = m.group('title')
    description = (parser.meta.get('mastodon:description')
                   or parser.meta.get('og:description')
                   or parser.meta.get('twitter:description'))
    tags = parser.meta.get('mastodon:tags')
    status = ""
    if title:
        status = f"{title}\n\n"
    if description:
        status += f"{description}\n"
    if BLOG_POST_POSTFIX:
        status += f"{BLOG_POST_POSTFIX}\n"
    if tags:
        status += f"{tags}\n"
    status += url
    return status


def get_toot_id(url, dryrun=False):
    if not url:
        raise BadRequest("No `url` query argument provided")
    if BLOG_POST_RE and not BLOG_POST_RE.match(url):
        logger.debug(f"url `{url}` is not handled")
        raise BadRequest("Provided `url` is not a handled")
    logger.debug(f"invoked for {url}")
    key = get_s3_key(url)
    try:
        response = _get_s3().head_object(Bucket=S3_BUCKET, Key=key)
        toot_id = response.get('Metadata', {}).get('toot-id')
        if toot_id:
            return int(toot_id)
    except ClientError as e:
        if e.response['Error']['Code'] != '404':
            raise
    toot_id = create_toot(url, dryrun=dryrun)
    if not dryrun:
        _get_s3().put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=b'',
            Metadata={'toot-id': str(toot_id)}
        )
        logger.info(f"resolved {url} to toot_id {toot_id}")
    return toot_id


def create_toot(url, dryrun=False):
    logger.debug(f"creating toot for {url}")
    status = build_status(url)
    if dryrun:
        logger.info(f"[dryrun] would post toot:\n{status}")
        return None
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
                elif k == 'name':
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
