import json
import logging
import sys

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(levelname)s] %(module)s %(message)s"
)

from service import MASTODON_HOST, MASTODON_USER, BadRequest, get_toot_id

logger = logging.getLogger(__name__)

JSON_HEADER = {'Content-Type': 'application/json'}
CORS_HEADER = {'Access-Control-Allow-Origin': '*'}


def _handle(url, extra_headers=None):
    """Core request logic shared by all entry points."""
    headers = {**JSON_HEADER, **(extra_headers or {})}
    try:
        toot_id = get_toot_id(url)
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(dict(host=MASTODON_HOST, user=MASTODON_USER, toot_id=str(toot_id)))
        }
    except BadRequest as e:
        return {'statusCode': 400, 'headers': headers,
                'body': json.dumps(dict(code=400, error=e.args[0]))}
    except Exception:
        logger.exception(f"request for {url} failed")
        return {'statusCode': 500, 'headers': headers,
                'body': json.dumps(dict(code=500, error='Internal server error'))}


def main(args):
    """DO Functions entry point — runtime handles CORS."""
    return _handle(args.get('url'))


def handler(event, context):
    """AWS Lambda entry point (API Gateway proxy integration)."""
    return _handle((event.get('queryStringParameters') or {}).get('url'), CORS_HEADER)


if __name__ == '__main__':
    import pprint
    url = sys.argv[1] if len(sys.argv) > 1 else None
    if not url:
        print("Usage: python __main__.py <url>", file=sys.stderr)
        sys.exit(1)
    pprint.pprint(_handle(url))
