"""Affichage des médias et téléchargement pour les types non prévisualisés."""

from __future__ import annotations

import functools
import hashlib
import html
import importlib.util
import io
import mimetypes
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import streamlit as st

# Rendu image page par page (PyMuPDF) — défilement continu dans le conteneur, compatible Chrome
_MAX_PDF_PAGES_RASTER = 100
# Au-delà : on tente quand même le raster (aperçu plafonné à _MAX_PDF_PAGES_RASTER pages affichables).
_MAX_PDF_BYTES_SOFT_WARN = 48 * 1024 * 1024
# Limite « dure » : au-delà, on ne tente plus le défilement continu (risque mémoire / lenteur) — mode page par page.
_MAX_PDF_BYTES_NO_CONTINUOUS = 256 * 1024 * 1024
_PDF_RASTER_ZOOM = 1.45
_PDF_RASTER_ZOOM_DIALOG = 2.2
_PDF_CONTAINER_HEIGHT = 880
_PDF_CONTAINER_HEIGHT_DIALOG = 1200

_PDF_PREVIEW_INITIAL_PAGES = 6
_PDF_PREVIEW_PAGE_STEP = 8
_JPEG_QUALITY_PDF = 78
_JPEG_QUALITY_THUMB = 72
_JPEG_QUALITY_DISPLAY = 85
_GALLERY_MAIN_MAX_WIDTH = 1400
_THUMB_MAX_SIDE = 132
_PREFETCH_THUMB_WORKERS = 6
_THUMB_DISPLAY_WIDTH = 110
_GALLERY_SEGMENT_MAX = 24

# Formats souvent concernés par EXIF Orientation : éviter st.image(chemin) brut (navigateur incohérent).
_EXIF_ORIENTATION_SUFFIXES = frozenset(
    {".jpg", ".jpeg", ".jpe", ".jfif", ".tif", ".tiff", ".bmp"}
)


def _gallery_caption_name(path: Path, *, max_len: int = 26) -> str:
    name = path.name
    if len(name) > max_len:
        return name[: max_len - 1] + "…"
    return name


def _streamlit_pdf_component_available() -> bool:
    """L’extra streamlit[pdf] installe le paquet streamlit-pdf (pas PyMuPDF sous le nom pymupdf)."""
    return importlib.util.find_spec("streamlit_pdf") is not None


def _pdf_expand_button_key(file_path: Path) -> str:
    h = hashlib.sha256(str(file_path.resolve()).encode("utf-8")).hexdigest()[:16]
    return f"pe_pdf_expand_{h}"


def _clear_pdf_dialog_state() -> None:
    st.session_state.pop("pe_pdf_dialog_path", None)
    st.session_state.pop("pe_pdf_dialog_mode", None)


def _path_stat_key(path: Path) -> tuple[str, int]:
    p = path.resolve()
    try:
        return str(p), int(p.stat().st_mtime_ns)
    except OSError:
        return str(p), 0


@st.cache_data(show_spinner=False, max_entries=256)
def _cached_pdf_page_count(resolved_norm: str, mtime_ns: int) -> int | None:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return None
    try:
        doc = fitz.open(resolved_norm)
        try:
            n = len(doc)
            return n if n > 0 else None
        finally:
            doc.close()
    except Exception:
        return None


@st.cache_data(show_spinner=False, max_entries=600)
def _cached_pdf_page_jpeg(
    resolved_norm: str,
    mtime_ns: int,
    page_index: int,
    zoom: float,
) -> bytes | None:
    """Une page PDF en JPEG (mis en cache par fichier / mtime / page / zoom)."""
    try:
        import fitz  # PyMuPDF
        from PIL import Image
    except ImportError:
        return None
    try:
        doc = fitz.open(resolved_norm)
    except Exception:
        return None
    try:
        if page_index < 0 or page_index >= len(doc):
            return None
        page = doc.load_page(page_index)
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        im = _pixmap_to_pil_rgb(pix)
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=_JPEG_QUALITY_PDF, optimize=False)
        return buf.getvalue()
    except Exception:
        return None
    finally:
        doc.close()


def _pixmap_to_pil_rgb(pix: Any) -> Any:
    from PIL import Image

    if pix.n == 1:
        return Image.frombytes("L", (pix.width, pix.height), pix.samples).convert("RGB")
    if pix.n == 3:
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    if pix.n == 4:
        im = Image.frombytes("RGBA", (pix.width, pix.height), pix.samples)
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[3])
        return bg
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def _render_pdf_raster_pages(
    file_path: Path,
    *,
    container_height: int,
    zoom: float,
    pages_to_render: int,
) -> bool:
    """Affiche les `pages_to_render` premières pages (JPEG en cache) dans un conteneur à défilement."""
    path_s, mtime_ns = _path_stat_key(file_path)
    if pages_to_render <= 0:
        return False
    try:
        with st.container(height=container_height, border=True):
            for i in range(pages_to_render):
                jpeg = _cached_pdf_page_jpeg(path_s, mtime_ns, i, zoom)
                if not jpeg:
                    return False
                st.image(io.BytesIO(jpeg), width="stretch")
        return True
    except Exception:
        return False


def _pdf_preview_limit_key(file_path: Path) -> str:
    path_s, _ = _path_stat_key(file_path)
    h = hashlib.sha256(path_s.encode("utf-8")).hexdigest()[:16]
    return f"pe_pdf_show_{h}"


def _try_pdf_raster_continuous_scroll(file_path: Path) -> bool:
    """Aperçu : quelques pages d’abord, puis « Charger plus » ; rendu mis en cache (plafonné)."""
    try:
        sz = file_path.stat().st_size
    except OSError:
        return False
    if sz == 0:
        return False
    # Très gros fichiers : pas de bandeau « toutes les pages » — le mode page par page prendra le relais.
    if sz > _MAX_PDF_BYTES_NO_CONTINUOUS:
        return False
    if sz > _MAX_PDF_BYTES_SOFT_WARN:
        st.caption(
            "Fichier volumineux : le défilement continu peut être lent au premier chargement (pages mises en cache ensuite)."
        )

    path_s, mtime_ns = _path_stat_key(file_path)
    n = _cached_pdf_page_count(path_s, mtime_ns)
    if n is None:
        return False
    n_cap = min(n, _MAX_PDF_PAGES_RASTER)

    ss_key = _pdf_preview_limit_key(file_path)
    if ss_key not in st.session_state:
        st.session_state[ss_key] = min(_PDF_PREVIEW_INITIAL_PAGES, n_cap)

    want = int(st.session_state[ss_key])
    want = max(1, min(want, n_cap))
    st.session_state[ss_key] = want
    pages_to_render = min(n_cap, want)

    ok = _render_pdf_raster_pages(
        file_path,
        container_height=_PDF_CONTAINER_HEIGHT,
        zoom=_PDF_RASTER_ZOOM,
        pages_to_render=pages_to_render,
    )
    if not ok:
        return False

    if n > _MAX_PDF_PAGES_RASTER:
        st.caption(
            f"Document de {n} pages — aperçu limité aux {_MAX_PDF_PAGES_RASTER} premières dans ce mode (défilement)."
        )
    if n_cap > pages_to_render:
        if st.button(
            "Charger plus de pages",
            key=f"{ss_key}_more",
            width="stretch",
            help=f"Ajoute jusqu’à {_PDF_PREVIEW_PAGE_STEP} pages à l’aperçu (déjà affichées : {pages_to_render} / {n_cap}).",
        ):
            st.session_state[ss_key] = min(n_cap, want + _PDF_PREVIEW_PAGE_STEP)
            st.rerun()
        st.caption(
            f"Aperçu partiel : {pages_to_render} / {n_cap} page(s) affichées — les pages rendues sont mises en cache."
        )
    return True


def _pdf_ui_prefs_key(file_path: Path) -> str:
    path_s, _ = _path_stat_key(file_path)
    h = hashlib.sha256(path_s.encode("utf-8")).hexdigest()[:16]
    return f"pe_pdf_scroll_{h}"


def _pdf_paginated_session_key(file_path: Path, prefix: str) -> str:
    path_s, _ = _path_stat_key(file_path)
    h = hashlib.sha256(path_s.encode("utf-8")).hexdigest()[:16]
    return f"pe_pdf1_{prefix}_{h}"


def _render_pdf_paginated_viewer(
    file_path: Path,
    *,
    zoom: float,
    container_height: int,
    key_prefix: str,
) -> bool:
    """Une seule page dans le DOM + navigation (adapté aux gros PDF). Retourne False si PyMuPDF indisponible ou PDF illisible."""
    try:
        import fitz  # noqa: F401
    except ImportError:
        return False
    path_s, mtime_ns = _path_stat_key(file_path)
    n = _cached_pdf_page_count(path_s, mtime_ns)
    if n is None or n <= 0:
        return False
    sk_sl = _pdf_paginated_session_key(file_path, f"{key_prefix}_pg")
    pg = st.slider("Page", min_value=1, max_value=n, key=sk_sl)
    idx = int(pg) - 1
    st.caption(f"Page {idx + 1} / {n}")
    jpeg = _cached_pdf_page_jpeg(path_s, mtime_ns, idx, zoom)
    if not jpeg:
        st.warning("Rendu de cette page impossible.")
        return True
    with st.container(height=container_height, border=True):
        st.image(io.BytesIO(jpeg), width="stretch")
    return True


def _pdf_expand_controls(file_path: Path, *, dialog_uses_fitz: bool) -> None:
    """Bouton « Agrandir » + ouverture de la boîte de dialogue pour le même fichier."""
    key = _pdf_expand_button_key(file_path)
    resolved = str(file_path.resolve())
    if st.button("🔍 Agrandir la fenêtre PDF", key=key, width="stretch", help="Ouvre un aperçu plus grand dans une fenêtre modale."):
        st.session_state["pe_pdf_dialog_path"] = resolved
        st.session_state["pe_pdf_dialog_mode"] = "fitz" if dialog_uses_fitz else "stpdf"
    if st.session_state.get("pe_pdf_dialog_path") == resolved:
        _pdf_enlarged_dialog()


@st.dialog(
    "Aperçu PDF agrandi",
    width="large",
    on_dismiss=_clear_pdf_dialog_state,
)
def _pdf_enlarged_dialog() -> None:
    path_s = st.session_state.get("pe_pdf_dialog_path")
    mode = st.session_state.get("pe_pdf_dialog_mode", "fitz")
    if not path_s:
        return
    p = Path(path_s)
    if mode == "fitz":
        path_key, mtime_ns = _path_stat_key(p)
        if _cached_pdf_page_count(path_key, mtime_ns) is None:
            st.caption("Lecture du PDF impossible.")
            mode = "stpdf"
        else:
            _render_pdf_paginated_viewer(
                p,
                zoom=_PDF_RASTER_ZOOM_DIALOG,
                container_height=_PDF_CONTAINER_HEIGHT_DIALOG,
                key_prefix="dlg",
            )
    if mode == "stpdf":
        try:
            st.pdf(str(p), height="stretch")
        except Exception as exc:
            st.error(f"Lecture du PDF impossible : {exc}")
    if st.button("Fermer", width="stretch"):
        _clear_pdf_dialog_state()
        st.rerun()


def _jpeg_try_draft(im: Any, max_w: int, max_h: int) -> None:
    """Demande un décodage JPEG/MPO déjà réduit (souvent beaucoup plus rapide que full decode)."""
    if getattr(im, "format", None) not in ("JPEG", "MPO"):
        return
    try:
        im.draft("RGB", (max_w, max_h))
    except Exception:
        try:
            im.draft("L", (max_w, max_h))
        except Exception:
            pass


def _pil_apply_exif_transpose(im: Any) -> Any:
    """Applique la balise EXIF Orientation (photos smartphone / appareils photo)."""
    try:
        from PIL import ImageOps
    except ImportError:
        return im
    try:
        return ImageOps.exif_transpose(im)
    except Exception:
        return im


def _pil_to_rgb(im: Any) -> Any:
    from PIL import Image

    if im.mode in ("RGB", "L"):
        return im.convert("RGB") if im.mode == "L" else im
    if im.mode == "RGBA":
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[3])
        return bg
    if im.mode == "P":
        return im.convert("RGBA").convert("RGB")
    if im.mode in ("LA", "PA"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[3])
        return bg
    return im.convert("RGB")


@functools.lru_cache(maxsize=512)
def _image_pixel_size_cached(path_str: str, mtime_ns: int) -> tuple[int, int] | None:
    """Lit largeur/hauteur (clé mtime pour invalider si le fichier change)."""
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        with Image.open(path_str) as im:
            im = _pil_apply_exif_transpose(im)
            return im.size
    except Exception:
        return None


def _image_pixel_size(path: Path) -> tuple[int, int] | None:
    path_s, mtime_ns = _path_stat_key(path)
    return _image_pixel_size_cached(path_s, mtime_ns)


@st.cache_data(show_spinner=False, max_entries=1024)
def _cached_image_jpeg_display(path_str: str, mtime_ns: int, max_width: int, quality: int) -> bytes | None:
    """Image redimensionnée (largeur max) pour aperçu fluide."""
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        with Image.open(path_str) as im:
            if getattr(im, "is_animated", False):
                im.seek(0)
            _jpeg_try_draft(im, max_width, max_width)
            im.load()
            im = _pil_apply_exif_transpose(im)
            rgb = _pil_to_rgb(im)
            w, h = rgb.size
            if w > max_width:
                nh = max(1, int(h * (max_width / w)))
                rgb = rgb.resize((max_width, nh), Image.Resampling.BICUBIC)
            buf = io.BytesIO()
            rgb.save(buf, format="JPEG", quality=quality, optimize=False)
            return buf.getvalue()
    except Exception:
        return None


@st.cache_data(show_spinner=False, max_entries=1024)
def _cached_image_jpeg_thumb(path_str: str, mtime_ns: int, max_side: int, quality: int) -> bytes | None:
    """Vignette carrée max (côté), JPEG."""
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        with Image.open(path_str) as im:
            if getattr(im, "is_animated", False):
                im.seek(0)
            # Décoder vers ~2× la vignette : moins de pixels qu’en pleine résolution
            _jpeg_try_draft(im, max_side * 3, max_side * 3)
            im.load()
            im = _pil_apply_exif_transpose(im)
            rgb = _pil_to_rgb(im)
            rgb.thumbnail((max_side, max_side), Image.Resampling.BILINEAR)
            buf = io.BytesIO()
            rgb.save(buf, format="JPEG", quality=quality, optimize=False)
            return buf.getvalue()
    except Exception:
        return None


def _warm_gallery_thumb_cache(paths: list[Path]) -> None:
    """Préremplit le cache des vignettes en parallèle (premier affichage plus fluide)."""
    if len(paths) <= 1:
        return

    def warm_one(p: Path) -> None:
        path_s, mtime_ns = _path_stat_key(p)
        dims = _image_pixel_size_cached(path_s, mtime_ns)
        if dims is not None and max(dims[0], dims[1]) <= _THUMB_MAX_SIDE:
            return
        _cached_image_jpeg_thumb(path_s, mtime_ns, _THUMB_MAX_SIDE, _JPEG_QUALITY_THUMB)

    n = len(paths)
    workers = min(_PREFETCH_THUMB_WORKERS, n)
    if workers < 2:
        for p in paths:
            warm_one(p)
        return
    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(warm_one, paths))


def _st_image_cached_or_raw(path: Path, *, max_width: int | None, thumb_side: int | None) -> None:
    """
    Aperçu image : si le fichier est déjà assez petit en pixels, envoi direct au navigateur
    (évite décodage complet + ré-encodage JPEG — souvent la cause des lenteurs sur JPG « web »).
    JPEG/TIFF/BMP passent toujours par PIL + EXIF Orientation pour un rendu cohérent.
    Sinon vignette / aperçu redimensionné mis en cache.
    """
    path_s, mtime_ns = _path_stat_key(path)
    dims = _image_pixel_size(path)
    use_exif_safe_pipeline = path.suffix.lower() in _EXIF_ORIENTATION_SUFFIXES

    if dims is not None and not use_exif_safe_pipeline:
        w, h = dims
        if thumb_side is not None:
            if max(w, h) <= thumb_side:
                st.image(path, width=_THUMB_DISPLAY_WIDTH)
                return
        if max_width is not None and w <= max_width:
            st.image(path, width="stretch")
            return

    if thumb_side is not None:
        b = _cached_image_jpeg_thumb(path_s, mtime_ns, thumb_side, _JPEG_QUALITY_THUMB)
        if b:
            st.image(io.BytesIO(b), width=_THUMB_DISPLAY_WIDTH)
            return
    if max_width is not None:
        b = _cached_image_jpeg_display(path_s, mtime_ns, max_width, _JPEG_QUALITY_DISPLAY)
        if b:
            st.image(io.BytesIO(b), width="stretch")
            return
    st.image(path, width="stretch")


def display_pdf_file(file_path: Path) -> None:
    """Affiche un PDF (par défaut une page à la fois ; défilement continu en option ; lecteur intégré en secours)."""
    mime_type, _ = mimetypes.guess_type(str(file_path))
    path_s, mtime_ns = _path_stat_key(file_path)
    n_pages = _cached_pdf_page_count(path_s, mtime_ns)
    dialog_uses_fitz = n_pages is not None

    try:
        file_uri = file_path.resolve().as_uri()
    except ValueError:
        file_uri = ""

    row = st.columns([1, 1])
    with row[0]:
        if file_uri:
            st.link_button(
                "Ouvrir dans une nouvelle fenêtre",
                file_uri,
                help="Ouvre le PDF avec le lecteur par défaut (navigateur ou Adobe, selon le système). "
                "Si le navigateur bloque les liens file://, enregistrez le fichier ou utilisez le dossier du projet.",
                width="stretch",
            )
    with row[1]:
        scroll_key = _pdf_ui_prefs_key(file_path)
        use_scroll = st.toggle(
            "Défilement continu",
            key=scroll_key,
            help="Plusieurs pages en JPEG dans un panneau défilant. Désactivé par défaut (une page à la fois, plus léger).",
        )

    raster_ok = False
    if use_scroll:
        raster_ok = _try_pdf_raster_continuous_scroll(file_path)
        if raster_ok:
            st.caption("Aperçu en défilement continu (pages rendues en JPEG, cache activé).")
        elif dialog_uses_fitz:
            st.caption("Défilement continu indisponible pour ce fichier — affichage page par page.")

    if not raster_ok:
        if _render_pdf_paginated_viewer(
            file_path,
            zoom=_PDF_RASTER_ZOOM,
            container_height=_PDF_CONTAINER_HEIGHT,
            key_prefix="main",
        ):
            if not use_scroll:
                st.caption("Aperçu page par page (défaut).")
        else:
            try:
                try:
                    sz = file_path.stat().st_size
                except OSError:
                    sz = 0
                if sz > _MAX_PDF_BYTES_SOFT_WARN:
                    st.caption(
                        "Fichier volumineux : lecteur intégré Streamlit (peut charger tout le document dans le navigateur)."
                    )
                st.pdf(str(file_path), height="stretch")
            except Exception as exc:
                hint = (
                    "L’aperçu intégré repose sur le paquet **streamlit-pdf** "
                    "(installé avec `pip install \"streamlit[pdf]\"` ou `pip install streamlit-pdf`). "
                    "Utilisez le **même interpréteur Python** que pour lancer Streamlit (ex. le `.venv` du projet)."
                )
                if not _streamlit_pdf_component_available():
                    st.warning(f"{hint}\n\n*(module `streamlit_pdf` introuvable dans cet environnement)*")
                else:
                    st.warning(f"{hint}\n\n*Erreur : `{exc}`*")
                with open(file_path, "rb") as f:
                    st.download_button(
                        label="Télécharger le PDF",
                        data=f.read(),
                        file_name=file_path.name,
                        mime=mime_type or "application/pdf",
                        width="stretch",
                    )
                return

    _pdf_expand_controls(file_path, dialog_uses_fitz=dialog_uses_fitz)


def display_image_gallery(paths: list[Path], *, session_key_suffix: str) -> None:
    """Grande image, sélecteur type onglets (segmented) ou liste, puis bandeau de vignettes en lecture seule."""
    if not paths:
        return
    idx_key = f"pe_img_gal_{session_key_suffix}"
    if len(paths) == 1:
        _st_image_cached_or_raw(paths[0], max_width=_GALLERY_MAIN_MAX_WIDTH, thumb_side=None)
        return

    if idx_key not in st.session_state:
        st.session_state[idx_key] = 0
    idx = int(st.session_state[idx_key])
    idx = max(0, min(idx, len(paths) - 1))
    st.session_state[idx_key] = idx

    _st_image_cached_or_raw(paths[idx], max_width=_GALLERY_MAIN_MAX_WIDTH, thumb_side=None)

    _warm_gallery_thumb_cache(paths)

    if len(paths) <= _GALLERY_SEGMENT_MAX:
        st.segmented_control(
            "Image à afficher",
            options=list(range(len(paths))),
            format_func=lambda i: str(i + 1),
            key=idx_key,
            selection_mode="single",
            label_visibility="collapsed",
            width="stretch",
        )
    else:
        st.selectbox(
            "Image à afficher",
            options=list(range(len(paths))),
            format_func=lambda i: f"{i + 1}. {_gallery_caption_name(paths[i], max_len=48)}",
            key=idx_key,
            label_visibility="collapsed",
            width="stretch",
        )

    st.caption(
        "Vignettes : même ordre que la liste ci-dessus (tri : type de fichier, puis chemin). "
        "La sélection se fait au-dessus."
    )

    thumb_cols = 6
    sel = int(st.session_state.get(idx_key, idx))
    sel = max(0, min(sel, len(paths) - 1))
    for row_start in range(0, len(paths), thumb_cols):
        chunk = paths[row_start : row_start + thumb_cols]
        cols = st.columns(len(chunk))
        for j, p in enumerate(chunk):
            i = row_start + j
            with cols[j]:
                _st_image_cached_or_raw(p, max_width=None, thumb_side=_THUMB_MAX_SIDE)
                label = _gallery_caption_name(p)
                if i == sel:
                    safe = html.escape(label, quote=True)
                    st.markdown(
                        f"<p style='margin:0.35rem 0 0;font-size:0.78rem;font-weight:600;"
                        f"color:#0c4a6e;border-top:2px solid #0ea5e9;padding-top:0.25rem'>"
                        f"{i + 1}. {safe}</p>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.caption(f"{i + 1}. {label}")


def display_linked_file(file_path: Path, *, show_filename_header: bool = True) -> None:
    """Affiche ou propose le téléchargement selon l'extension (lecture du fichier à l'appel)."""
    suffix = file_path.suffix.lower()
    mime_type, _ = mimetypes.guess_type(str(file_path))

    if show_filename_header:
        st.write(f"**Fichier trouvé** : `{file_path.name}`")
        st.caption(str(file_path))

    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}:
        _st_image_cached_or_raw(file_path, max_width=_GALLERY_MAIN_MAX_WIDTH, thumb_side=None)
        return

    if suffix == ".pdf":
        display_pdf_file(file_path)
        return

    if suffix in {".mp3", ".wav", ".m4a", ".ogg", ".flac"}:
        st.audio(str(file_path))
        return

    if suffix in {".mp4", ".mov", ".webm", ".mkv"}:
        st.video(str(file_path))
        return

    if suffix == ".odt":
        mime_type = mime_type or "application/vnd.oasis.opendocument.text"
        with open(file_path, "rb") as f:
            st.download_button(
                label="Télécharger le document ODT (LibreOffice)",
                data=f.read(),
                file_name=file_path.name,
                mime=mime_type,
                width="stretch",
            )
        return

    with open(file_path, "rb") as f:
        st.download_button(
            label="Télécharger le fichier",
            data=f.read(),
            file_name=file_path.name,
            mime=mime_type or "application/octet-stream",
            width="stretch",
        )
