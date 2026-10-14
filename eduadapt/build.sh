#!/usr/bin/env bash
set -o errexit
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py makemigrations core --no-input   # no-op when migrations are committed
python manage.py migrate --no-input
