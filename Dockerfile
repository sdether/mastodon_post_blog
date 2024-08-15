FROM python:3.11-slim

ENV APP_HOME /opt/mastodon-post-blog

RUN mkdir -p $APP_HOME/requirements

COPY ./requirements.txt ${APP_HOME}/
COPY ./requirements ${APP_HOME}/requirements/

RUN cd ${APP_HOME} && \
    python -m venv /opt/venv && \
    /opt/venv/bin/python -m pip install --progress-bar off -f requirements -r requirements.txt && \
    /opt/venv/bin/python -m pip install --progress-bar off gunicorn

ARG VERSION
ENV VERSION $VERSION

COPY ./postblog ${APP_HOME}/postblog/
COPY ./entrypoint.sh ${APP_HOME}/

RUN chmod +x ${APP_HOME}/entrypoint.sh

WORKDIR $APP_HOME

CMD ["./entrypoint.sh"]