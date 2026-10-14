#!/usr/bin/env bash
set -e
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py makemigrations core
python manage.py migrate
python manage.py runserver
