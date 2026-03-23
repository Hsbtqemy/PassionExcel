#!/usr/bin/env bash
# Lance l'application sur macOS ou Linux.
set -e
cd "$(dirname "$0")"

echo ""
echo "=== Consultation documentaire ==="
echo ""

pick_python() {
  for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
      if "$cmd" -c "import sys; sys.exit(0 if sys.version_info>=(3,11) else 1)" 2>/dev/null; then
        echo "$cmd"
        return 0
      fi
    fi
  done
  local base
  base="$(cd "$(dirname "$0")" && pwd)"
  local emb="$base/python/bin/python3"
  if [[ -x "$emb" ]] && "$emb" -c "import sys; sys.exit(0 if sys.version_info>=(3,11) else 1)" 2>/dev/null; then
    echo "$emb"
    return 0
  fi
  return 1
}

PY="$(pick_python || true)"
if [[ -z "$PY" ]]; then
  echo "[Erreur] Python 3.11 ou plus récent est requis."
  echo "Installez Python (python.org, brew, paquets système) ou placez un Python embarqué dans ./python/bin/python3"
  exit 1
fi

echo "Python utilisé : $PY"
echo ""

if [ ! -d ".venv" ]; then
  echo "Création de l'environnement virtuel local..."
  "$PY" -m venv .venv
fi

# shellcheck source=/dev/null
source ".venv/bin/activate"

echo "Installation ou mise à jour des dépendances..."
python -m pip install --upgrade pip >/dev/null
pip install -r requirements.txt

echo ""
echo "Lancement de l'application. Le navigateur va s'ouvrir."
echo "Interrompez avec Ctrl+C dans ce terminal pour arrêter."
echo ""
exec python -m streamlit run app.py
