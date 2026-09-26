#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --no-input

# Seed initial demo dataset only if database is fresh/empty
python -c "import django, os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edurev_swap.settings'); django.setup(); from accounts.models import User; from django.core.management import call_command; User.objects.exists() or call_command('seed_demo')"
