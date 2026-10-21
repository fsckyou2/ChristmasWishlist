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

# --- stylesheet: Tailwind's standalone CLI (pinned, checksum-verified) scans the templates and builds app.css -------
FROM python:${PYTHON_VERSION}-slim AS css
ARG TARGETARCH
ARG TAILWIND_VERSION=3.4.17
ARG TAILWIND_SHA256_AMD64=7d24f7fa191d2193b78cd5f5a42a6093e14409521908529f42d80b11fde1f1d4
ARG TAILWIND_SHA256_ARM64=69b1378b8133192d7d2feb12a116fa12d035594f58db3eff215879e4ad8cf39b
RUN set -eu; \
    case "${TARGETARCH:-amd64}" in \
        amd64) asset=tailwindcss-linux-x64; sha="${TAILWIND_SHA256_AMD64}" ;; \
        arm64) asset=tailwindcss-linux-arm64; sha="${TAILWIND_SHA256_ARM64}" ;; \
        *) echo "unsupported architecture: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    python -c "import sys, urllib.request; urllib.request.urlretrieve(sys.argv[1], sys.argv[2])" \
        "https://github.com/tailwindlabs/tailwindcss/releases/download/v${TAILWIND_VERSION}/${asset}" /usr/local/bin/tailwindcss; \
    echo "${sha}  /usr/local/bin/tailwindcss" | sha256sum -c -; \
    chmod 0755 /usr/local/bin/tailwindcss
WORKDIR /build
COPY tailwind.config.js ./
COPY app/static/css/input.css app/static/css/input.css
COPY app/templates app/templates
COPY app/static/js app/static/js
RUN tailwindcss -c tailwind.config.js -i app/static/css/input.css -o app/static/css/app.css --minify

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
COPY --from=css /build/app/static/css/app.css app/static/css/app.css
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
