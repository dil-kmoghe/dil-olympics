#!/bin/sh
set -eu

python manage.py migrate --noinput
python manage.py collectstatic --noinput

if [ -n "${SEED_EXCEL_PATH:-}" ] && [ -f "${SEED_EXCEL_PATH}" ]; then
  seed_args="--excel ${SEED_EXCEL_PATH}"
  if [ "${SEED_CREATE_ADMIN:-false}" = "true" ]; then
    seed_args="${seed_args} --create-admin"
  fi
  if [ "${SEED_CREATE_SCOREKEEPERS:-false}" = "true" ]; then
    seed_args="${seed_args} --create-scorekeepers"
  fi
  python manage.py seed_olympics ${seed_args}
else
  echo "Skipping seed: SEED_EXCEL_PATH is empty or file was not found."
fi

exec gunicorn olympics.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-2}" \
  --worker-class gthread \
  --threads "${GUNICORN_THREADS:-4}" \
  --timeout "${GUNICORN_TIMEOUT:-120}"
