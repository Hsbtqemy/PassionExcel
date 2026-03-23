#!/usr/bin/env bash
# Télécharge CPython « install_only » (indygreg/python-build-standalone) pour inclusion dans le .app.
# À lancer sur macOS avant build_app.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="$SCRIPT_DIR/embed/python"
TAG="20241016"
PYVER="3.12.7"

ARCH="$(uname -m)"
if [[ "$ARCH" == "arm64" ]]; then
  SUFFIX="aarch64-apple-darwin-install_only.tar.gz"
elif [[ "$ARCH" == "x86_64" ]]; then
  SUFFIX="x86_64-apple-darwin-install_only.tar.gz"
else
  echo "Architecture non supportée : $ARCH"
  exit 1
fi

NAME="cpython-${PYVER}+${TAG}-${SUFFIX}"
URL="https://github.com/astral-sh/python-build-standalone/releases/download/${TAG}/${NAME}"
TMP="$(mktemp -d)"

echo "→ Téléchargement : $URL"
curl -fsSL "$URL" -o "$TMP/python.tgz"
echo "→ Extraction..."
mkdir -p "$TMP/out"
tar -xzf "$TMP/python.tgz" -C "$TMP/out"
rm -rf "$TARGET"
mkdir -p "$(dirname "$TARGET")"
ROOT_DIR="$(find "$TMP/out" -mindepth 1 -maxdepth 1 -type d | head -1)"
if [[ -z "$ROOT_DIR" ]] || [[ ! -d "$ROOT_DIR/bin" ]]; then
  echo "Structure d'archive inattendue (bin/ introuvable)."
  exit 1
fi
mv "$ROOT_DIR" "$TARGET"
rm -rf "$TMP"

PY="$TARGET/bin/python3"
chmod +x "$PY" 2>/dev/null || true
echo "→ OK : $("$PY" -c 'import sys; print(sys.version)')"
