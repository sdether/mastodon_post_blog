import argparse
import json
import logging
import sys

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(levelname)s] %(module)s %(message)s"
)

from service import MASTODON_HOST, MASTODON_USER, BadRequest, build_status, get_toot_id

logger = logging.getLogger(__name__)

JSON_HEADER = {'Content-Type': 'application/json'}
CORS_HEADER = {'Access-Control-Allow-Origin': '*'}


def _handle(url, extra_headers=None, dryrun=False):
    """Core request logic shared by all entry points."""
    headers = {**JSON_HEADER, **(extra_headers or {})}
    try:
        toot_id = get_toot_id(url, dryrun=dryrun)
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

    parser = argparse.ArgumentParser(description='Post a blog URL to Mastodon')
    parser.add_argument('url', nargs='?', help='Blog post URL')
    parser.add_argument('--dryrun', action='store_true',
                        help='Run the full flow but skip posting the toot')
    parser.add_argument('--show-toot', action='store_true',
                        help='Print what the toot would look like and exit')
    args = parser.parse_args()

    if not args.url:
        parser.print_usage(sys.stderr)
        sys.exit(1)

    if args.show_toot:
        try:
            print(build_status(args.url))
        except BadRequest as e:
            print(f"Error: {e.args[0]}", file=sys.stderr)
            sys.exit(1)
    else:
        pprint.pprint(_handle(args.url, dryrun=args.dryrun))
