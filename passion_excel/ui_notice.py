"""Présentation type « fiche notice » : styles et blocs HTML pour une lecture confortable."""

from __future__ import annotations

import html
from pathlib import Path

import pandas as pd
import streamlit as st

from passion_excel.display import display_linked_file
from passion_excel.files import (
    MEDIA_KIND_LABELS_FR,
    collect_matching_paths,
    has_valid_path_roots,
    parse_file_names,
    parse_path_roots,
    preview_notice_files_count,
    suggest_paths_by_name_fragment,
)
from passion_excel.notice_helpers import normalize_value


def _esc(s: str) -> str:
    return html.escape(s, quote=True)


def _format_prose(text: str) -> str:
    """Préserve les retours à la ligne pour un bloc de lecture."""
    if not text.strip():
        return ""
    # Échapper puis convertir les sauts de ligne en <br>
    parts = text.splitlines()
    return "<br>".join(_esc(p) if p else "&nbsp;" for p in parts)


def inject_notice_styles() -> None:
    """Feuille de style globale pour l’app (cartes, typographie, grilles)."""
    st.markdown(
        """
<style>
  /* Cartes et hiérarchie */
  .pe-notice-shell {
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    color: #1c1917;
  }
  .pe-card {
    background: linear-gradient(180deg, #fafaf9 0%, #f5f5f4 100%);
    border: 1px solid #e7e5e4;
    border-radius: 14px;
    padding: 1.5rem 1.75rem 1.75rem;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    margin-bottom: 0.5rem;
  }
  .pe-card--doc {
    background: #fafafa;
    min-height: 120px;
  }
  .pe-kicker {
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #78716c;
    margin: 0 0 0.35rem 0;
  }
  .pe-notice-title {
    font-size: 1.65rem;
    font-weight: 650;
    line-height: 1.25;
    letter-spacing: -0.02em;
    color: #0c0a09;
    margin: 0 0 1rem 0;
    border-bottom: 1px solid #e7e5e4;
    padding-bottom: 0.85rem;
  }
  .pe-section-title {
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #57534e;
    margin: 1.25rem 0 0.5rem 0;
  }
  .pe-section-title:first-of-type {
    margin-top: 0.25rem;
  }
  .pe-prose {
    font-size: 1.02rem;
    line-height: 1.65;
    color: #292524;
    max-width: 52rem;
  }
  .pe-meta-grid {
    display: grid;
    grid-template-columns: minmax(7rem, 32%) 1fr;
    gap: 0.35rem 1rem;
    align-items: baseline;
    font-size: 0.95rem;
    line-height: 1.5;
    margin-top: 0.35rem;
  }
  @media (max-width: 640px) {
    .pe-meta-grid {
      grid-template-columns: 1fr;
    }
  }
  .pe-meta-k {
    color: #78716c;
    font-weight: 500;
    font-size: 0.82rem;
  }
  .pe-meta-v {
    color: #1c1917;
    word-break: break-word;
  }
  .pe-nav-strip {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem 0.75rem;
    background: #f5f5f4;
    border: 1px solid #e7e5e4;
    border-radius: 12px;
    padding: 0.65rem 1rem;
    margin-bottom: 1.1rem;
  }
  .pe-nav-badge {
    margin-left: auto;
    font-size: 0.85rem;
    font-weight: 600;
    color: #44403c;
    background: #fff;
    border: 1px solid #d6d3d1;
    border-radius: 999px;
    padding: 0.25rem 0.75rem;
  }
  .pe-doc-path {
    font-size: 0.78rem;
    color: #78716c;
    word-break: break-all;
    margin-top: 0.35rem;
  }
  .pe-empty-hint {
    font-size: 0.95rem;
    color: #57534e;
    line-height: 1.55;
  }
</style>
        """,
        unsafe_allow_html=True,
    )


def render_navigation_strip(position: int, total: int) -> None:
    """Bandeau visuel au-dessus du contenu (complète les boutons Streamlit)."""
    st.markdown(
        f"""
<div class="pe-notice-shell">
  <div class="pe-nav-strip">
    <span class="pe-kicker" style="margin:0;">Navigation</span>
    <span class="pe-nav-badge">Notice {position} sur {total}</span>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_notice_fiche(
    *,
    selected_row: pd.Series,
    df_columns: list[str],
    title_col: str,
    summary_col: str,
    meta_cols: list[str],
) -> None:
    """Bloc principal : titre, résumé, métadonnées en grille, repliable données brutes."""
    titre = normalize_value(selected_row.get(title_col, "")).strip() or "Sans titre"

    parts: list[str] = [
        '<div class="pe-notice-shell">',
        '<article class="pe-card" aria-label="Notice">',
        '<p class="pe-kicker">Fiche documentaire</p>',
        f'<h1 class="pe-notice-title">{_esc(titre)}</h1>',
    ]

    if summary_col != "(aucune)":
        resume = normalize_value(selected_row.get(summary_col, "")).strip()
        if resume:
            parts.append('<h2 class="pe-section-title">Résumé</h2>')
            parts.append(f'<div class="pe-prose">{_format_prose(resume)}</div>')

    if meta_cols:
        parts.append('<h2 class="pe-section-title">Informations</h2>')
        parts.append('<div class="pe-meta-grid">')
        for col in meta_cols:
            val = normalize_value(selected_row.get(col, "")).strip()
            parts.append(f'<div class="pe-meta-k">{_esc(str(col))}</div>')
            parts.append(f'<div class="pe-meta-v">{_esc(val) if val else "—"}</div>')
        parts.append("</div>")

    parts.append("</article></div>")

    st.markdown("".join(parts), unsafe_allow_html=True)

    with st.expander("Données brutes (toutes les colonnes du tableur)"):
        st.json({c: normalize_value(selected_row[c]) for c in df_columns})


def render_document_panel(
    *,
    selected_row: pd.Series,
    file_col: str,
    path_col: str,
    use_path_column: bool,
    assets_dir: str,
    assets_path: Path | None,
    assets_dir_valid: bool,
    media_kind: str = "all",
    selection_key: str | int | None = None,
) -> None:
    """Panneau droit : un ou plusieurs fichiers ; chemins relatifs optionnels sous la racine."""
    names = parse_file_names(selected_row.get(file_col))

    st.markdown(
        """
<div class="pe-notice-shell">
  <p class="pe-kicker" style="margin-bottom:0.5rem;">Documents associés</p>
</div>
        """,
        unsafe_allow_html=True,
    )

    if not names:
        st.markdown(
            '<div class="pe-card pe-card--doc"><p class="pe-empty-hint">'
            "Aucun nom de fichier n’est indiqué dans la colonne choisie "
            "(séparez plusieurs fichiers par point-virgule ou retour à la ligne)."
            "</p></div>",
            unsafe_allow_html=True,
        )
        return

    if not assets_dir.strip():
        st.markdown(
            '<div class="pe-card pe-card--doc"><p class="pe-empty-hint">'
            "Indiquez le <strong>dossier racine</strong> des documents dans la barre latérale "
            "pour afficher les fichiers.</p></div>",
            unsafe_allow_html=True,
        )
        return

    if not assets_dir_valid or assets_path is None:
        st.markdown(
            '<div class="pe-card pe-card--doc"><p class="pe-empty-hint">'
            "Le dossier indiqué est introuvable ou inaccessible. Vérifiez le chemin "
            "(lecteur, réseau, droits de lecture).</p></div>",
            unsafe_allow_html=True,
        )
        return

    path_subroots: list[str] | None
    if use_path_column:
        path_subroots = parse_path_roots(selected_row.get(path_col))
    else:
        path_subroots = None

    if use_path_column and path_subroots and not has_valid_path_roots(assets_path, path_subroots):
        st.markdown(
            """
<div class="pe-card pe-card--doc" style="border-color:#fecaca;background:#fef2f2;">
  <p class="pe-empty-hint" style="color:#991b1b;margin:0;">
    <strong>Dossiers introuvables.</strong> Aucun des chemins indiqués dans la colonne chemins relatifs
    n’existe pas sous le dossier racine. Vérifiez les noms de dossiers.
  </p>
</div>
            """,
            unsafe_allow_html=True,
        )
        return

    if use_path_column:
        pr_display = parse_path_roots(selected_row.get(path_col))
        if pr_display:
            zones = " ; ".join(pr_display)
            st.caption(f"Dossiers parcourus (sous la racine) : `{zones}` — recherche **récursive** dans chacun.")
        else:
            st.caption("Aucun sous-dossier imposé : recherche sur **toute** l’arborescence sous la racine.")

    kind_label = MEDIA_KIND_LABELS_FR.get(media_kind, media_kind)
    st.caption(f"Filtre de type actuel : **{kind_label}** (modifiable dans la barre latérale).")

    sk = selection_key if selection_key is not None else 0

    for i, expected in enumerate(names):
        st.markdown(
            f"""
<div class="pe-notice-shell">
  <div class="pe-card pe-card--doc">
    <p class="pe-kicker" style="margin-bottom:0.35rem;">Fichier {i + 1} / {len(names)}</p>
    <p style="margin:0;font-size:1rem;font-weight:600;color:#1c1917;">{_esc(expected)}</p>
  </div>
</div>
            """,
            unsafe_allow_html=True,
        )

        matches = collect_matching_paths(
            assets_path,
            expected,
            path_subroots=path_subroots,
            media_kind=media_kind,
        )

        resolved: Path | None = None
        if len(matches) > 1:
            opts = [str(p) for p in matches]
            chosen = st.selectbox(
                "Plusieurs fichiers correspondent — choisissez celui à prévisualiser :",
                options=opts,
                key=f"doc_disamb_{sk}_{i}",
            )
            resolved = Path(chosen)
        elif len(matches) == 1:
            resolved = matches[0]
        elif media_kind != "all":
            all_matches = collect_matching_paths(
                assets_path,
                expected,
                path_subroots=path_subroots,
                media_kind="all",
            )
            if len(all_matches) > 1:
                st.info(
                    f"Aucun fichier ne correspond au filtre « {kind_label} », mais d’autres extensions existent."
                )
                opts = [str(p) for p in all_matches]
                pick = st.selectbox(
                    "Choisir un fichier (tous types) :",
                    options=opts,
                    key=f"doc_fallback_{sk}_{i}",
                )
                resolved = Path(pick)
            elif len(all_matches) == 1:
                st.success(
                    f"Fichier trouvé en élargissant au type « Tous types » (filtre « {kind_label} » excluait cette extension)."
                )
                resolved = all_matches[0]

        if resolved is None:
            exp_path = Path(expected)
            frag = exp_path.stem if len(exp_path.stem) >= 2 else exp_path.name
            sugg = suggest_paths_by_name_fragment(
                assets_path,
                frag,
                path_subroots=path_subroots,
                media_kind=media_kind,
            )
            if not sugg and media_kind != "all":
                sugg = suggest_paths_by_name_fragment(
                    assets_path,
                    frag,
                    path_subroots=path_subroots,
                    media_kind="all",
                )
            st.markdown(
                f"""
<div class="pe-card pe-card--doc" style="border-color:#fecaca;background:#fef2f2;">
  <p class="pe-empty-hint" style="color:#991b1b;margin:0;">
    <strong>Introuvable</strong> pour ce nom dans les dossiers autorisés (avec le filtre actuel).
  </p>
</div>
                """,
                unsafe_allow_html=True,
            )
            if sugg:
                with st.expander("Suggestions : noms contenant « {} » (aperçu limité)".format(_esc(frag))):
                    for sp in sugg:
                        rel = str(sp)
                        st.caption(rel)
                        if sp.suffix.lower() in {
                            ".png",
                            ".jpg",
                            ".jpeg",
                            ".webp",
                            ".gif",
                            ".bmp",
                            ".tif",
                            ".tiff",
                        }:
                            st.image(sp, width=220)
            else:
                st.caption(
                    "Vérifiez l’orthographe, l’extension, ou que le fichier est bien sous la racine "
                    "(et dans les sous-dossiers indiqués si une colonne chemins est utilisée)."
                )
            continue

        st.markdown(
            f'<p class="pe-doc-path">Chemin résolu : {_esc(str(resolved))}</p>',
            unsafe_allow_html=True,
        )
        display_linked_file(resolved, show_filename_header=False)


def render_filtered_preview(
    filtered_df: pd.DataFrame,
    file_col: str,
    path_col: str,
    use_path_column: bool,
    assets_path: Path | None,
    assets_dir_valid: bool,
    media_kind: str = "all",
) -> None:
    """Aperçu tableau avec compteur fichiers trouvés / attendus."""
    st.markdown('<p class="pe-kicker">Aperçu du jeu filtré</p>', unsafe_allow_html=True)
    preview = filtered_df.copy()
    if assets_dir_valid and assets_path is not None and file_col in preview.columns:

        def _status(row: pd.Series) -> str:
            pc = row[path_col] if use_path_column and path_col in row.index else None
            found, total = preview_notice_files_count(
                assets_path,
                row[file_col],
                pc,
                use_path_column=use_path_column,
                media_kind=media_kind,
            )
            if total == 0:
                return "—"
            return f"{found}/{total}"

        preview["_fichiers_trouvés"] = preview.apply(_status, axis=1)
    st.dataframe(preview, use_container_width=True, hide_index=False)
