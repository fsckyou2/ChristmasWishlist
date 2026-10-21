#!/usr/bin/env sh
# Build app/static/css/app.css for local development (the Docker image builds its own).
# Downloads the pinned Tailwind standalone CLI into .cache/ once and checks its sha256.
set -eu
cd "$(dirname "$0")/.."

VERSION=3.4.17
case "$(uname -s)-$(uname -m)" in
    Linux-x86_64) ASSET=tailwindcss-linux-x64 SHA=7d24f7fa191d2193b78cd5f5a42a6093e14409521908529f42d80b11fde1f1d4 ;;
    Linux-aarch64 | Linux-arm64) ASSET=tailwindcss-linux-arm64 SHA=69b1378b8133192d7d2feb12a116fa12d035594f58db3eff215879e4ad8cf39b ;;
    Darwin-arm64) ASSET=tailwindcss-macos-arm64 SHA=a1d0c7985759accca0bf12e51ac1dcbf0f6cf2fffb62e6e0f62d091c477a10a3 ;;
    Darwin-x86_64) ASSET=tailwindcss-macos-x64 SHA=6cbdad74be776c087ffa5e9a057512c54898f9fe8828d3362212dfe32fc933a3 ;;
    MINGW*-x86_64 | MSYS*-x86_64) ASSET=tailwindcss-windows-x64.exe SHA=67f1c5e3f5a03406a7bf5badf5ada09b79f3ae78ec43450c15f7e983068da346 ;;
    *) echo "No Tailwind CLI for $(uname -s)-$(uname -m); build the Docker image instead." >&2; exit 1 ;;
esac

CLI=".cache/tailwindcss-$VERSION-$ASSET"
if [ ! -x "$CLI" ]; then
    mkdir -p .cache
    curl -fsSL -o "$CLI.part" "https://github.com/tailwindlabs/tailwindcss/releases/download/v$VERSION/$ASSET"
    echo "$SHA  $CLI.part" | sha256sum -c - >/dev/null
    chmod +x "$CLI.part"
    mv "$CLI.part" "$CLI"
fi

"$CLI" -c tailwind.config.js -i app/static/css/input.css -o app/static/css/app.css --minify "$@"
