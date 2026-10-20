# syntax=docker/dockerfile:1
ARG PYTHON_VERSION=3.13

# --- dependencies (built once, copied into the final images) -------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS deps
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

FROM deps AS dev-deps
COPY requirements-dev.txt /tmp/requirements-dev.txt
RUN pip install -r /tmp/requirements-dev.txt

# --- application -----------------------------------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS app-base
# Runs as an unprivileged user. 568 is the "apps" user/group on TrueNAS SCALE; override with --build-arg if needed.
ARG APP_UID=568
ARG APP_GID=568
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH \
    FLASK_APP=run:app \
    APP_ENV=production
RUN groupadd --system --gid "${APP_GID}" app \
    && useradd --system --uid "${APP_UID}" --gid app --home-dir /app --no-create-home --shell /usr/sbin/nologin app
WORKDIR /app
# Code is owned by root and read-only to the app user; only instance/ (the database) is writable.
COPY . .
RUN chmod 0755 docker-entrypoint.sh \
    && mkdir -p instance \
    && chown app:app instance
EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/healthz', timeout=3)"]
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["web"]

# Development image (tests, linters): docker build --target dev .
FROM app-base AS dev
COPY --from=dev-deps /opt/venv /opt/venv
USER app:app

# Production image (default target)
FROM app-base AS runtime
COPY --from=deps /opt/venv /opt/venv
USER app:app
