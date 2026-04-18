from logging.config import dictConfig

dictConfig({
    'version': 1,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'urllib3': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
        'requests': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
    },
    'root': {'level': 'DEBUG', 'handlers': ['console']},
})

import logging

from flask import Flask, request

from service import MASTODON_HOST, MASTODON_USER, BadRequest, get_toot_id

logger = logging.getLogger(__name__)

app = Flask(__name__)
application = app

CORS_HEADERS = {'Access-Control-Allow-Origin': '*'}


@app.route('/status')
def status():
    return dict(code=200, message='OK')


@app.route('/')
def postblog():
    url = None
    try:
        url = request.args.get('url')
        toot_id = get_toot_id(url)
        return (
            dict(host=MASTODON_HOST, user=MASTODON_USER, toot_id=str(toot_id)),
            200,
            CORS_HEADERS,
        )
    except BadRequest as e:
        return (dict(code=400, error=e.args[0]), 400, CORS_HEADERS)
    except Exception:
        logger.exception(f"request for {url} failed")
        raise
