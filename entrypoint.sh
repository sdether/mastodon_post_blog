#!/bin/bash

echo "starting flask app"
/opt/venv/bin/gunicorn postblog.app  --bind "0.0.0.0:8000"
