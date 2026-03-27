"""Présentation type « fiche notice » : styles et blocs HTML pour une lecture confortable."""

from __future__ import annotations

import hashlib
import html
from pathlib import Path

import pandas as pd
import streamlit as st

from passion_excel.display import display_image_gallery, display_linked_file, display_pdf_file
from passion_excel.shell_open import open_folder
from passion_excel.files import (
    MEDIA_KIND_LABELS_FR,
    collect_matching_paths,
    has_valid_path_roots,
    parse_file_names,
    parse_path_roots,
    preview_notice_files_count,
    sort_paths_for_display,
    split_matches_pdf_images,
    suggest_paths_by_name_fragment,
)
from passion_excel.notice_helpers import normalize_value


def _esc(s: str) -> str:
    return html.escape(s, quote=True)


def _render_file_links(paths: list[Path], *, key_prefix: str) -> None:
    """Liens file:// vers chaque fichier (ouverture avec l’application par défaut du système)."""
    if not paths:
        return
    st.caption("Ouvrir avec l’application par défaut (lien local) :")
    for j, p in enumerate(paths):
        try:
            uri = p.resolve().as_uri()
        except ValueError:
            uri = ""
        label = p.name if len(p.name) <= 72 else p.name[:69] + "…"
        if not uri:
            st.caption(f"• `{label}` — lien indisponible.")
            continue
        st.link_button(label, uri, key=f"pe_lk_{key_prefix}_{j}", help=str(p))


def _dedupe_file_names_ordered(names: list[str]) -> list[str]:
    """Évite les doublons (souvent dus aux exports) tout en conservant l’ordre."""
    seen: set[str] = set()
    out: list[str] = []
    for n in names:
        t = n.strip()
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def _cell_display_str(value: object) -> str:
    """Représentation texte stable pour colonnes pandas « object » (évite erreurs Arrow int/bytes/str mélangés)."""
    try:
        if pd.isna(value):
            return ""
    except (ValueError, TypeError):
        pass
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", errors="replace")
    return str(value)


def _sanitize_dataframe_for_streamlit(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise les colonnes « object » pour la sérialisation Arrow de st.dataframe."""
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == object:
            out[col] = out[col].map(_cell_display_str)
    return out


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
  /* Erreur / infos : fonds opaques (les alertes natives Streamlit sont souvent en pastel « lavé ») */
  .pe-file-error,
  .pe-file-error *,
  .pe-doc-info,
  .pe-doc-info * {
    opacity: 1 !important;
  }
  .pe-doc-info {
    border: 1px solid #bfdbfe;
    background: #eff6ff;
    border-radius: 14px;
    padding: 1rem 1.15rem;
    margin-bottom: 0.75rem;
    color: #1e3a8a;
    font-size: 0.95rem;
    line-height: 1.55;
  }
  /* Colonne documents + Markdown HTML : forcer l’opacité (évite un rendu grisé sous les visualiseurs) */
  section.main [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(2):last-child) > [data-testid="column"]:last-child,
  section.main [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(2):last-child) > [data-testid="column"]:last-child * {
    opacity: 1 !important;
  }
  section.main [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(2),
  section.main [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(2) * {
    opacity: 1 !important;
  }
  section.main [data-testid="column"] [data-testid="stMarkdownContainer"] {
    opacity: 1 !important;
  }
  section.main [data-testid="stVerticalBlockBorderWrapper"],
  section.main [data-testid="stVerticalBlockBorderWrapper"] * {
    opacity: 1 !important;
  }

  /* Zone principale : 2 colonnes (fiche + documents) — 60/40 sur grand écran, pile en dessous du breakpoint */
  @media (min-width: 960px) {
    section.main [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(2):last-child) {
      flex-wrap: nowrap !important;
      align-items: flex-start !important;
    }
    section.main [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(2):last-child)
      > [data-testid="column"]:nth-child(1) {
      flex: 0 0 60% !important;
      max-width: 60% !important;
      min-width: 0 !important;
    }
    section.main [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(2):last-child)
      > [data-testid="column"]:nth-child(2) {
      flex: 0 0 40% !important;
      max-width: 40% !important;
      min-width: 0 !important;
    }
  }
  @media (max-width: 959px) {
    section.main [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(2):last-child) {
      flex-direction: column !important;
      flex-wrap: nowrap !important;
      align-items: stretch !important;
    }
    section.main [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(2):last-child)
      > [data-testid="column"] {
      flex: 1 1 auto !important;
      width: 100% !important;
      max-width: 100% !important;
      min-width: 0 !important;
    }
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
) -> None:
    """Panneau droit : un ou plusieurs fichiers ; chemins relatifs optionnels sous la racine."""
    names = _dedupe_file_names_ordered(parse_file_names(selected_row.get(file_col)))

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

    r1, r2 = st.columns(2)
    with r1:
        try:
            root_uri = assets_path.resolve().as_uri()
        except ValueError:
            root_uri = ""
        if root_uri:
            st.link_button(
                "Dossier racine (lien)",
                root_uri,
                key="pe_root_uri_link",
                help="Ouvre le dossier racine des documents (comportement selon le système).",
            )
    with r2:
        if st.button(
            "Dossier racine dans l’explorateur",
            key="pe_root_shell_open",
            help="Ouvre le dossier racine dans le gestionnaire de fichiers.",
        ):
            ok, err = open_folder(assets_path)
            if not ok:
                st.warning(f"Impossible d’ouvrir le dossier : {err}")

    if len(names) > 1:
        st.markdown(
            f"""
<div class="pe-doc-info">
  <strong>{len(names)} noms de fichiers</strong> sont listés pour cette notice (séparateurs : <code>;</code> <code>|</code> ou retour à la ligne).
  Chaque bloc ci-dessous est indépendant : un fichier peut s’afficher correctement alors qu’un autre est signalé introuvable.
</div>
            """,
            unsafe_allow_html=True,
        )

    for i, expected in enumerate(names):
        with st.container(border=True):
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
            display_paths: list[Path] = []
            if len(matches) >= 1:
                resolved = matches[0]
                display_paths = list(matches)
                if len(matches) > 1:
                    st.caption(
                        f"{len(matches)} fichiers correspondent ; affichage du plus pertinent "
                        "(images avant PDF, puis autres types, puis ordre des chemins)."
                    )
            elif media_kind != "all":
                all_matches = collect_matching_paths(
                    assets_path,
                    expected,
                    path_subroots=path_subroots,
                    media_kind="all",
                )
                if len(all_matches) >= 1:
                    resolved = all_matches[0]
                    display_paths = list(all_matches)
                    if len(all_matches) > 1:
                        st.caption(
                            f"Aucun fichier pour le filtre « {kind_label} » ; {len(all_matches)} fichier(s) en « Tous types » "
                            "— affichage du premier."
                        )
                    else:
                        st.success(
                            f"Fichier trouvé en élargissant au type « Tous types » (le filtre « {kind_label} » excluait cette extension)."
                        )

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
                if sugg:
                    sugg = sort_paths_for_display(sugg)
                    resolved = sugg[0]
                    display_paths = list(sugg)
                    if len(sugg) > 1:
                        st.caption(
                            f"{len(sugg)} fichiers dont le nom contient « {frag} » ; affichage automatique du premier."
                        )
                    else:
                        st.caption("Fichier détecté par correspondance partielle du nom.")

            if resolved is None:
                st.markdown(
                    f"""
<div class="pe-file-error pe-card pe-card--doc" style="border:1px solid #fecaca;background:#fef2f2 !important;box-shadow:none;">
  <p class="pe-empty-hint" style="color:#991b1b !important;margin:0;opacity:1 !important;">
    <strong>Introuvable :</strong> « {_esc(expected)} » — aucune correspondance dans les dossiers autorisés
    (filtre <strong>{_esc(kind_label)}</strong>). Vérifiez l’orthographe, l’extension, la racine ou la colonne chemins.
  </p>
</div>
                    """,
                    unsafe_allow_html=True,
                )
                continue

            if not display_paths:
                display_paths = [resolved]

            pdfs, imgs = split_matches_pdf_images(display_paths)
            gal_suffix = hashlib.sha256(f"{expected}|{i}".encode("utf-8")).hexdigest()[:16]
            key_pdf = f"pe_show_pdf_{gal_suffix}"
            key_img = f"pe_show_img_{gal_suffix}"
            skip: set[Path] = set()

            col_left, col_right = st.columns([3, 1])
            with col_left:
                st.markdown(
                    f'<p class="pe-doc-path">Chemin résolu : {_esc(str(resolved))}</p>',
                    unsafe_allow_html=True,
                )
                _render_file_links(display_paths, key_prefix=gal_suffix)
            with col_right:
                st.caption("Aperçu intégré")
                if pdfs:
                    if st.button(
                        "Charger PDF",
                        key=f"{key_pdf}_btn",
                        help="Affiche le lecteur PDF dans l’application.",
                    ):
                        st.session_state[key_pdf] = True
                if imgs:
                    if st.button(
                        "Charger images",
                        key=f"{key_img}_btn",
                        help="Affiche la galerie d’images dans l’application.",
                    ):
                        st.session_state[key_img] = True
                try:
                    folder_uri = resolved.parent.resolve().as_uri()
                except ValueError:
                    folder_uri = ""
                if folder_uri:
                    st.link_button(
                        "Dossier (lien)",
                        folder_uri,
                        key=f"pe_fold_uri_{gal_suffix}",
                        help="Ouvre le dossier parent du fichier résolu.",
                    )
                if st.button(
                    "Dossier (explorateur)",
                    key=f"pe_fold_sh_{gal_suffix}",
                    help="Ouvre le dossier parent dans le gestionnaire de fichiers.",
                ):
                    ok, err = open_folder(resolved)
                    if not ok:
                        st.warning(f"Impossible d’ouvrir le dossier : {err}")

            if pdfs and st.session_state.get(key_pdf, False):
                display_pdf_file(pdfs[0])
                skip.add(pdfs[0])
            if imgs and st.session_state.get(key_img, False):
                display_image_gallery(imgs, session_key_suffix=gal_suffix)
                skip.update(imgs)
            if not pdfs and not imgs:
                display_linked_file(resolved, show_filename_header=False)
            else:
                for p in display_paths:
                    if p in skip:
                        continue
                    display_linked_file(p, show_filename_header=False)


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
    st.dataframe(
        _sanitize_dataframe_for_streamlit(preview),
        width="stretch",
        hide_index=False,
    )
