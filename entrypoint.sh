#!/bin/bash
set -e
exec /opt/venv/bin/gunicorn --bind 0.0.0.0:8000 --chdir packages/postblog/post app:application
