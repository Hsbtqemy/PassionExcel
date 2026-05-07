#!/usr/bin/env bash
# Construit PassionExcel.app et une archive DMG (à exécuter sur macOS).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUT_DIR="$SCRIPT_DIR/dist"
APP_BUNDLE="PassionExcel.app"

if [[ ! -x "$SCRIPT_DIR/embed/python/bin/python3" ]] && [[ -f "$SCRIPT_DIR/prepare_embed_python.sh" ]]; then
  echo "→ Préparation de Python embarqué (téléchargement, ~40 Mo)..."
  chmod +x "$SCRIPT_DIR/prepare_embed_python.sh" 2>/dev/null || true
  "$SCRIPT_DIR/prepare_embed_python.sh" || echo "→ (Poursuite sans Python embarqué — Python système requis sur la machine cible)"
fi

rm -rf "$OUT_DIR/$APP_BUNDLE"
mkdir -p "$OUT_DIR/$APP_BUNDLE/Contents/MacOS"
mkdir -p "$OUT_DIR/$APP_BUNDLE/Contents/Resources/app"

echo "→ Copie des fichiers depuis $REPO_ROOT ..."
rsync -a --delete \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude 'installer' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  "$REPO_ROOT/" "$OUT_DIR/$APP_BUNDLE/Contents/Resources/app/"

cp "$SCRIPT_DIR/Info.plist" "$OUT_DIR/$APP_BUNDLE/Contents/Info.plist"
cp "$SCRIPT_DIR/PassionExcel" "$OUT_DIR/$APP_BUNDLE/Contents/MacOS/PassionExcel"
chmod +x "$OUT_DIR/$APP_BUNDLE/Contents/MacOS/PassionExcel"

if [[ -d "$SCRIPT_DIR/embed/python/bin" ]]; then
  echo "→ Copie de Python embarqué..."
  mkdir -p "$OUT_DIR/$APP_BUNDLE/Contents/Resources"
  rsync -a "$SCRIPT_DIR/embed/python/" "$OUT_DIR/$APP_BUNDLE/Contents/Resources/python/"
else
  echo "→ (Pas de dossier installer/mac/embed/python — l’app utilisera le Python système si disponible)"
fi

echo "→ Paquet créé : $OUT_DIR/$APP_BUNDLE"

if command -v hdiutil &>/dev/null; then
  VER="${VERSION:-$(/usr/libexec/PlistBuddy -c 'Print CFBundleShortVersionString' "$SCRIPT_DIR/Info.plist" 2>/dev/null || echo "0.0.0")}"
  DMG="$OUT_DIR/PassionExcel_mac_${VER}.dmg"
  rm -f "$DMG"
  rm -f "$OUT_DIR/.dmg-tmp.dmg" 2>/dev/null || true
  echo "→ Création du DMG..."
  hdiutil create -volname "Passion Excel" -srcfolder "$OUT_DIR/$APP_BUNDLE" -ov -format UDZO "$DMG"
  echo "→ $DMG"
else
  echo "(hdiutil absent, DMG non créé — normal hors macOS)"
fi

echo "Terminé."
