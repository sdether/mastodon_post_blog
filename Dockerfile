FROM python:3.11-slim

ENV APP_HOME /opt/mastodon-post-blog

COPY packages/postblog/post/requirements.txt ${APP_HOME}/packages/postblog/post/

RUN python -m venv /opt/venv && \
    /opt/venv/bin/python -m pip install --progress-bar off \
        -r ${APP_HOME}/packages/postblog/post/requirements.txt \
        Flask==3.0.3 \
        gunicorn

COPY packages/postblog/post/service.py ${APP_HOME}/packages/postblog/post/
COPY packages/postblog/post/app.py     ${APP_HOME}/packages/postblog/post/
COPY entrypoint.sh ${APP_HOME}/

RUN chmod +x ${APP_HOME}/entrypoint.sh

WORKDIR ${APP_HOME}

CMD ["./entrypoint.sh"]
