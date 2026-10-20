#!/bin/sh
# Container entrypoint. Runs as the unprivileged app user (see Dockerfile).
#   web        migrate the database, ensure the admin user exists, then serve with gunicorn (default)
#   scheduler  run the periodic-job worker (daily digest)
#   anything else is executed as-is, e.g. `flask create-invite --note "Aunt Rebecca"`
set -eu

case "${1:-web}" in
    web)
        flask init-db
        flask bootstrap-admin
        exec gunicorn \
            --bind 0.0.0.0:5000 \
            --workers "${GUNICORN_WORKERS:-2}" \
            --threads "${GUNICORN_THREADS:-4}" \
            --timeout 60 \
            --graceful-timeout 8 \
            --worker-tmp-dir /dev/shm \
            --no-control-socket \
            --access-logfile - \
            run:app
        ;;
    scheduler)
        exec python scheduler_worker.py
        ;;
    *)
        exec "$@"
        ;;
esac
