"""Résolution des chemins vers les fichiers liés (racine, dossiers ciblés, type de média)."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

# Extensions par catégorie (filtrage de la recherche)
EXT_BY_KIND: dict[str, frozenset[str] | None] = {
    "all": None,
    "image": frozenset({".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}),
    "pdf": frozenset({".pdf"}),
    "audio": frozenset({".mp3", ".wav", ".m4a", ".ogg", ".flac"}),
    "video": frozenset({".mp4", ".mov", ".webm", ".mkv"}),
    "office": frozenset({".odt", ".ods", ".docx", ".xlsx", ".doc", ".ppt", ".pptx", ".rtf", ".pdf"}),
    "other": None,
}

_UNION_TYPED = frozenset().union(
    *(EXT_BY_KIND[k] for k in ("image", "pdf", "audio", "video", "office") if EXT_BY_KIND[k]),
)

# Extensions essayées si le tableur ne donne pas de suffixe (selon le type choisi)
STEM_FALLBACK_BY_KIND: dict[str, tuple[str, ...]] = {
    "all": (".pdf", ".png", ".jpg", ".jpeg", ".odt", ".ods", ".docx", ".xlsx", ".mp3", ".mp4"),
    "image": (".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff", ".bmp"),
    "pdf": (".pdf",),
    "audio": (".mp3", ".wav", ".m4a", ".ogg", ".flac"),
    "video": (".mp4", ".mov", ".webm", ".mkv"),
    "office": (".pdf", ".odt", ".ods", ".docx", ".xlsx", ".doc", ".ppt", ".pptx"),
    "other": (".txt", ".zip", ".7z", ".csv", ".xml", ".json"),
}

MEDIA_KIND_LABELS_FR: dict[str, str] = {
    "all": "Tous types",
    "image": "Images",
    "pdf": "PDF",
    "audio": "Audio",
    "video": "Vidéo",
    "office": "Bureautique (Office, ODF…)",
    "other": "Autres extensions",
}


def media_kind_options() -> list[tuple[str, str]]:
    """Paires (libellé FR, clé) pour un selectbox."""
    order = ("all", "image", "pdf", "audio", "video", "office", "other")
    return [(MEDIA_KIND_LABELS_FR[k], k) for k in order]


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


def _suffix_matches_media(suffix: str, media_kind: str) -> bool:
    s = suffix.lower()
    if media_kind == "all":
        return True
    if media_kind == "other":
        return bool(s) and s not in _UNION_TYPED
    exts = EXT_BY_KIND.get(media_kind)
    if exts is None:
        return True
    return s in exts


def _dedupe_sorted(paths: list[Path], root_resolved: Path) -> list[Path]:
    seen: set[str] = set()
    out: list[Path] = []
    for p in sorted(paths, key=lambda x: str(x).lower()):
        key = str(p.resolve())
        if key not in seen:
            seen.add(key)
            out.append(p)
    return [p for p in out if _is_under_root(p, root_resolved)]


def collect_matching_paths(
    root_dir: str | Path,
    file_name: str,
    *,
    path_subroots: list[str] | None = None,
    media_kind: str = "all",
) -> list[Path]:
    """Tous les chemins valides correspondant au nom / au type (pour désambiguïsation ou suggestions)."""
    root = Path(root_dir).expanduser()
    if not root.exists() or not root.is_dir():
        return []

    raw = (file_name or "").strip()
    if not raw:
        return []

    rel = Path(raw)
    if rel.is_absolute():
        return []

    root_resolved = root.resolve()
    bases = _search_bases(root_resolved, path_subroots)
    if bases is None:
        return []

    matches: list[Path] = []
    base_name = rel.name
    stem_fallback_exts = STEM_FALLBACK_BY_KIND.get(media_kind, STEM_FALLBACK_BY_KIND["all"])

    for base in bases:
        candidate = (base / rel).resolve()
        if candidate.is_file() and _is_under_root(candidate, root_resolved) and _suffix_matches_media(
            candidate.suffix,
            media_kind,
        ):
            matches.append(candidate)

        for path in base.rglob(base_name):
            if path.is_file() and _is_under_root(path, root_resolved) and _suffix_matches_media(
                path.suffix,
                media_kind,
            ):
                matches.append(path)

        # Nom sans extension dans le tableur : essayer stem + extensions du type choisi
        if not rel.suffix and rel.name:
            for ext in stem_fallback_exts:
                if not _suffix_matches_media(ext, media_kind):
                    continue
                c2 = (base / rel.with_suffix(ext)).resolve()
                if c2.is_file() and _is_under_root(c2, root_resolved):
                    matches.append(c2)
                # Un seul segment (ex. CD-AE-01-001) : chercher ce nom de fichier dans toute l’arborescence
                if len(rel.parts) == 1:
                    leaf = f"{rel.stem}{ext}"
                    for path in base.rglob(leaf):
                        if path.is_file() and _is_under_root(path, root_resolved) and _suffix_matches_media(
                            path.suffix,
                            media_kind,
                        ):
                            matches.append(path)

    return _dedupe_sorted(matches, root_resolved)


def resolve_linked_file(
    root_dir: str | Path,
    file_name: str,
    *,
    path_subroots: list[str] | None = None,
    media_kind: str = "all",
) -> Path | None:
    """Retourne le premier fichier trouvé (liste triée). Pour plusieurs correspondances, utiliser l’UI de choix."""
    paths = collect_matching_paths(root_dir, file_name, path_subroots=path_subroots, media_kind=media_kind)
    return paths[0] if paths else None


def resolve_linked_file_relaxed(
    root_dir: str | Path,
    file_name: str,
    *,
    path_subroots: list[str] | None = None,
) -> Path | None:
    """Comme resolve sans filtre de type (pour message d’aide si le filtre masque un fichier existant)."""
    return resolve_linked_file(root_dir, file_name, path_subroots=path_subroots, media_kind="all")


def suggest_paths_by_name_fragment(
    root_dir: str | Path,
    fragment: str,
    *,
    path_subroots: list[str] | None = None,
    media_kind: str = "all",
    max_results: int = 24,
    max_scanned: int = 12000,
) -> list[Path]:
    """Fichiers dont le nom contient la chaîne (recherche limitée pour rester réactive)."""
    root = Path(root_dir).expanduser()
    if not root.is_dir() or not fragment.strip():
        return []
    root_resolved = root.resolve()
    bases = _search_bases(root_resolved, path_subroots)
    if bases is None:
        return []
    frag = fragment.strip().lower()
    out: list[Path] = []
    scanned = 0
    for base in bases:
        for p in base.rglob("*"):
            scanned += 1
            if scanned > max_scanned:
                return _dedupe_sorted(out, root_resolved)[:max_results]
            if not p.is_file() or not _is_under_root(p, root_resolved):
                continue
            if frag not in p.name.lower():
                continue
            if _suffix_matches_media(p.suffix, media_kind):
                out.append(p)
                if len(out) >= max_results:
                    return _dedupe_sorted(out, root_resolved)
    return _dedupe_sorted(out, root_resolved)


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
    media_kind: str = "all",
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
        if resolve_linked_file(root_dir, fn, path_subroots=ps, media_kind=media_kind) is not None:
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
