"""Résolution des chemins vers les fichiers liés (racine, dossiers ciblés, sous-arborescences)."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


def _is_na(value: object) -> bool:
    try:
        return bool(pd.isna(value))
    except Exception:
        return False


def split_list_cell(value: object, *, allow_comma: bool = True) -> list[str]:
    """Découpe une cellule en plusieurs jetons (séparateurs : saut de ligne, ; | ; éventuellement ,)."""
    if value is None or _is_na(value):
        return []
    s = str(value).strip()
    if not s:
        return []
    if re.search(r"[\n;|]", s):
        parts = re.split(r"[\n;|]+", s)
        return [p.strip() for p in parts if p.strip()]
    if allow_comma and "," in s:
        parts = s.split(",")
        return [p.strip() for p in parts if p.strip()]
    return [s]


def parse_file_names(cell: object) -> list[str]:
    """Noms de fichiers (une notice peut en lister plusieurs)."""
    return split_list_cell(cell, allow_comma=True)


def parse_path_roots(cell: object) -> list[str]:
    """Chemins relatifs sous la racine des documents (plusieurs dossiers possibles). Pas de virgule pour éviter les ambiguïtés."""
    if cell is None or _is_na(cell):
        return []
    s = str(cell).strip()
    if not s:
        return []
    if re.search(r"[\n;|]", s):
        parts = re.split(r"[\n;|]+", s)
        return [_normalize_rel_segment(p) for p in parts if p.strip()]
    return [_normalize_rel_segment(s)]


def _normalize_rel_segment(seg: str) -> str:
    seg = seg.strip().replace("\\", "/").strip("/")
    return seg


def _safe_subpath(root_resolved: Path, rel: str) -> Path | None:
    """Construit root/rel sans sortir de la racine (rejette .. et chemins absolus)."""
    rel = rel.strip()
    if not rel:
        return None
    p = Path(rel)
    if p.is_absolute():
        return None
    if ".." in p.parts:
        return None
    candidate = (root_resolved / p).resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError:
        return None
    return candidate


def _search_bases(root_resolved: Path, path_subroots: list[str] | None) -> list[Path] | None:
    """Bases de recherche : sous-dossiers donnés ou la racine seule.

    - ``path_subroots is None`` : colonne « chemins » non utilisée → recherche sous toute la racine.
    - ``path_subroots == []`` : cellule vide → idem, toute la racine.
    - ``path_subroots == ["a","b"]`` : uniquement sous ``racine/a`` et ``racine/b`` (récursif par nom).

    Retourne ``None`` si des chemins étaient listés mais aucun dossier valide sous la racine.
    """
    if path_subroots is None or not path_subroots:
        return [root_resolved]
    bases: list[Path] = []
    for seg in path_subroots:
        sp = _safe_subpath(root_resolved, seg)
        if sp is not None and sp.is_dir():
            bases.append(sp)
    if not bases:
        return None
    return bases


def resolve_linked_file(
    root_dir: str | Path,
    file_name: str,
    *,
    path_subroots: list[str] | None = None,
) -> Path | None:
    """Retrouve un fichier sous la racine des ressources.

    - ``file_name`` : nom simple ou chemin relatif (ex. ``doc.pdf`` ou ``sous/dossier/doc.pdf``).
    - ``path_subroots`` : si fourni et non vide, limite la recherche à ces dossiers (relatifs à la racine),
      chacun étant parcouru **récursivement** pour un fichier du même nom de base.
      Si ``None`` ou liste vide, comportement global : d’abord ``racine / chemin_du_fichier``, puis ``rglob``
      sur toute l’arborescence sous la racine.
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
    bases = _search_bases(root_resolved, path_subroots)
    if bases is None:
        return None

    base_name = rel.name

    for base in bases:
        candidate = (base / rel).resolve()
        if _is_under_root(candidate, root_resolved) and candidate.is_file():
            return candidate

        for path in base.rglob(base_name):
            if path.is_file() and _is_under_root(path, root_resolved):
                return path

    return None


def _is_under_root(path: Path, root_resolved: Path) -> bool:
    try:
        path.resolve().relative_to(root_resolved)
    except ValueError:
        return False
    return True


def has_valid_path_roots(root_dir: str | Path, path_subroots: list[str]) -> bool:
    """Vrai si aucun sous-dossier n'est imposé, ou si au moins un des dossiers listés existe sous la racine."""
    if not path_subroots:
        return True
    root = Path(root_dir).expanduser()
    if not root.is_dir():
        return False
    bases = _search_bases(root.resolve(), path_subroots)
    return bases is not None


def preview_notice_files_count(
    root_dir: str | Path,
    file_cell: object,
    path_cell: object | None,
    *,
    use_path_column: bool,
) -> tuple[int, int]:
    """Compte (trouvés, total) pour l’aperçu tableau."""
    names = parse_file_names(file_cell)
    if not names:
        return 0, 0
    if use_path_column:
        ps: list[str] | None = parse_path_roots(path_cell)
    else:
        ps = None
    found = 0
    for fn in names:
        if resolve_linked_file(root_dir, fn, path_subroots=ps) is not None:
            found += 1
    return found, len(names)


def preview_file_found(
    root_dir: str | Path,
    file_cell: object,
    *,
    cache: dict[str, bool],
) -> bool:
    """Indique si un nom de fichier est trouvable (cache par clé simple — compat aperçu minimal)."""
    key = str(file_cell).strip() if file_cell is not None and not _is_na(file_cell) else ""
    if not key:
        return False
    if key in cache:
        return cache[key]
    found = resolve_linked_file(root_dir, key) is not None
    cache[key] = found
    return found
