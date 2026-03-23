"""Résolution des chemins vers les fichiers liés (racine puis sous-dossiers)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def resolve_linked_file(root_dir: str | Path, file_name: str) -> Path | None:
    """Retrouve un fichier à partir de la racine des ressources et du nom dans le tableur.

    Stratégie :
    1. Essayer ``racine / chemin_relatif`` tel qu'indiqué dans la cellule (ex. ``doc.pdf`` ou ``sous/dossier/doc.pdf``).
    2. Si introuvable, rechercher le premier fichier dont le nom de base correspond (parcours récursif).

    Les chemins absolus dans le tableur sont ignorés (sécurité : tout reste sous la racine).
    Aucun contenu de fichier n'est lu ici : uniquement des tests d'existence sur le disque.
    """
    root = Path(root_dir).expanduser()
    if not root.exists() or not root.is_dir():
        return None

    raw = (file_name or "").strip()
    if not raw:
        return None

    rel = Path(raw)
    if rel.is_absolute():
        return None

    root_resolved = root.resolve()

    # 1) Chemin direct relatif à la racine
    candidate = (root / rel).resolve()
    if _is_under_root(candidate, root_resolved) and candidate.is_file():
        return candidate

    # 2) Recherche par nom de fichier dans l'arborescence
    base = rel.name
    for path in root_resolved.rglob(base):
        if path.is_file() and _is_under_root(path, root_resolved):
            return path

    return None


def _is_under_root(path: Path, root_resolved: Path) -> bool:
    """Vérifie que ``path`` résolu reste sous ``root_resolved``."""
    try:
        path.resolve().relative_to(root_resolved)
    except ValueError:
        return False
    return True


def preview_file_found(
    root_dir: str | Path,
    cell_value: object,
    *,
    cache: dict[str, bool],
) -> bool:
    """Indique si un nom de fichier est trouvable (avec cache par nom normalisé)."""
    if cell_value is None or pd.isna(cell_value):
        return False
    key = str(cell_value).strip()
    if not key:
        return False
    if key in cache:
        return cache[key]
    found = resolve_linked_file(root_dir, key) is not None
    cache[key] = found
    return found
