"""
Application Streamlit : consultation de notices à partir d'un tableur et de fichiers locaux.

Lancer : streamlit run app.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from passion_excel.loader import (
    list_table_sheets,
    list_table_sheets_from_path,
    load_table_from_path,
    load_table_from_upload,
)
from passion_excel.notice_helpers import (
    build_record_label,
    get_notice_position,
)
from passion_excel.search import row_matches_query
from passion_excel.folder_picker import TkNotAvailableError, pick_folder, pick_table_file
from passion_excel.files import media_kind_options
from passion_excel.ui_notice import (
    inject_notice_styles,
    render_document_panel,
    render_filtered_preview,
    render_navigation_strip,
    render_notice_fiche,
)

# ---------------------------------------------------------------------------
# Cache Streamlit : évite de relire le tableur à chaque interaction légère
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner=False)
def _cached_load_upload(file_bytes: bytes, file_name: str, sheet_name: str | None) -> pd.DataFrame:
    return load_table_from_upload(file_bytes, file_name, sheet_name)


@st.cache_data(show_spinner=False)
def _cached_list_sheets_upload(file_bytes: bytes, file_name: str) -> list[str]:
    return list_table_sheets(file_bytes, file_name)


@st.cache_data(show_spinner=False)
def _cached_load_path(table_path: str, sheet_name: str | None) -> pd.DataFrame:
    return load_table_from_path(table_path, sheet_name)


@st.cache_data(show_spinner=False)
def _cached_list_sheets_path(table_path: str) -> list[str]:
    return list_table_sheets_from_path(table_path)


def _table_file_needs_sheet_picker(lower_name: str) -> bool:
    """Fichiers avec plusieurs feuilles (ou un seul tableau ODT à nommer)."""
    return lower_name.endswith((".xlsx", ".ods", ".odt"))


# ---------------------------------------------------------------------------
# Configuration de page
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Consultation documentaire",
    page_icon="📚",
    layout="wide",
)

if "selected_index" not in st.session_state:
    st.session_state.selected_index = None
if "assets_dir" not in st.session_state:
    st.session_state.assets_dir = ""
if "table_path" not in st.session_state:
    st.session_state.table_path = ""

# ---------------------------------------------------------------------------
# Interface — barre latérale (source, dossier, mapping, filtres)
# ---------------------------------------------------------------------------

st.markdown(
    """
<div style="margin-bottom:0.25rem;">
  <span style="font-size:1.5rem;font-weight:650;letter-spacing:-0.02em;color:#0c0a09;">
    Consultation documentaire
  </span>
</div>
    """,
    unsafe_allow_html=True,
)
st.caption(
    "Lisez vos notices comme des fiches : texte à gauche, document à droite. "
    "Données issues de votre tableur, fichiers sur votre ordinateur."
)

with st.sidebar:
    st.header("1. Fichier tabulaire")
    source_mode = st.radio(
        "Source",
        options=["Téléverser un fichier", "Chemin sur cet ordinateur"],
        help="Le mode « chemin » lit le fichier là où il se trouve, sans copie dans l’application.",
    )

    uploaded_file = None

    if source_mode == "Téléverser un fichier":
        uploaded_file = st.file_uploader(
            "Choisir un tableur (CSV, Excel, OpenDocument)",
            type=["csv", "xlsx", "ods", "odt"],
            help="Formats : CSV, Excel .xlsx, LibreOffice Calc .ods, texte LibreOffice Writer .odt (premier tableau du document).",
        )
    else:
        if st.button(
            "📄 Choisir le fichier sur cet ordinateur…",
            key="btn_pick_table_file",
            use_container_width=True,
            help="Ouvre l’explorateur pour un fichier CSV, Excel, ODS ou ODT.",
        ):
            try:
                chosen = pick_table_file("Choisir le tableur (CSV ou Excel)")
                if chosen:
                    st.session_state.table_path = chosen
                    st.rerun()
            except TkNotAvailableError as e:
                st.warning(str(e))
            except Exception as e:
                st.warning(f"Impossible d’ouvrir le sélecteur de fichier : {e}")

        st.text_input(
            "Chemin du tableur (modifiable)",
            key="table_path",
            placeholder=r"Ex. C:\Corpus\notices.ods",
            help="Vous pouvez aussi coller un chemin ici si le bouton ci-dessus ne fonctionne pas (session distante, etc.).",
        )

    st.header("2. Dossier des documents liés")
    if st.button(
        "📁 Choisir le dossier des documents…",
        key="btn_pick_assets_dir",
        use_container_width=True,
        help="Ouvre l’explorateur pour choisir le dossier racine du corpus (images, PDF, etc.).",
    ):
        try:
            chosen = pick_folder("Dossier racine des documents liés")
            if chosen:
                st.session_state.assets_dir = chosen
                st.rerun()
        except TkNotAvailableError as e:
            st.warning(str(e))
        except Exception as e:
            st.warning(f"Impossible d’ouvrir le sélecteur de dossier : {e}")

    st.text_input(
        "Dossier racine du corpus (modifiable)",
        key="assets_dir",
        placeholder=r"Ex. C:\Corpus\documents",
        help="Point de départ sur le disque. Les chemins du tableur sont relatifs à ce dossier.",
    )

    st.caption(
        "Les **fichiers** sont repérés par **nom** (une ou plusieurs entrées séparées par `;` ou retour à la ligne). "
        "Optionnellement, une colonne **chemins** limite la recherche à certains sous-dossiers de cette racine."
    )

    st.subheader("Type de média attendu")
    _media_labels, _media_keys = zip(*media_kind_options(), strict=True)
    _label_for = dict(zip(_media_keys, _media_labels, strict=True))
    media_kind = st.selectbox(
        "Filtrer la recherche par extension",
        options=list(_media_keys),
        format_func=lambda k: _label_for[k],
        key="media_kind_filter",
        help="Affine les correspondances (ex. PDF uniquement). Si le tableur n’indique pas l’extension, "
        "des variantes typiques du type choisi sont essayées.",
    )

    table_path = ""
    if source_mode == "Chemin sur cet ordinateur":
        table_path = str(st.session_state.get("table_path", "") or "")
    assets_dir = str(st.session_state.get("assets_dir", "") or "")

# ---------------------------------------------------------------------------
# Chargement du tableur
# ---------------------------------------------------------------------------

try:
    df: pd.DataFrame | None = None
    sheet_name: str | None = None

    if source_mode == "Téléverser un fichier":
        if uploaded_file is None:
            st.info("Chargez un fichier tabulaire : CSV, Excel (.xlsx), Calc (.ods) ou Writer (.odt, premier tableau).")
            st.stop()

        file_bytes = uploaded_file.getvalue()
        lower_name = uploaded_file.name.lower()

        if _table_file_needs_sheet_picker(lower_name):
            sheets = _cached_list_sheets_upload(file_bytes, uploaded_file.name)
            sheet_name = st.sidebar.selectbox(
                "Feuille / tableau",
                sheets,
                key="sheet_upload",
                help="Excel / Calc : choix de la feuille. ODT : le premier tableau du fichier est chargé (libellé indicatif).",
            )

        df = _cached_load_upload(file_bytes, uploaded_file.name, sheet_name)

    else:
        if not table_path.strip():
            st.info("Indiquez le chemin d’un fichier CSV, Excel, ODS ou ODT sur cet ordinateur.")
            st.stop()

        path = Path(table_path.strip())
        if not path.is_file():
            st.error("Ce chemin n’est pas un fichier valide ou le fichier est introuvable.")
            st.stop()

        lower_name = path.name.lower()
        sheet_name = None
        if _table_file_needs_sheet_picker(lower_name):
            sheets = _cached_list_sheets_path(table_path.strip())
            sheet_name = st.sidebar.selectbox(
                "Feuille / tableau",
                sheets,
                key="sheet_path",
                help="Excel / Calc : feuille à lire. ODT : premier tableau du document.",
            )

        df = _cached_load_path(table_path.strip(), sheet_name)

except Exception as exc:
    err = str(exc).lower()
    if "odfpy" in err:
        st.error(
            "Les fichiers **.ods** et **.odt** nécessitent le paquet **odfpy**, souvent absent si les dépendances "
            "n’ont pas été réinstallées.\n\n"
            "Dans le même environnement Python que Streamlit, exécutez :\n\n"
            "`pip install odfpy`  ou  `pip install -r requirements.txt`\n\n"
            "Puis relancez l’application."
        )
    elif "openpyxl" in err:
        st.error(
            "Les fichiers **.xlsx** nécessitent **openpyxl**. Exécutez : `pip install openpyxl` "
            "ou `pip install -r requirements.txt`, puis relancez."
        )
    else:
        st.error(f"Impossible de lire le tableur : {exc}")
    st.stop()

if df is None or df.empty:
    st.warning("Le tableur ne contient aucune ligne.")
    st.stop()

# Noms de colonnes : espaces bords uniquement (les valeurs restent inchangées)
df = df.copy()
df.columns = [str(c).strip() for c in df.columns]

# ---------------------------------------------------------------------------
# Mapping et filtres (barre latérale)
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("3. Colonnes affichées")
    title_col = st.selectbox("Titre de la notice", options=list(df.columns), index=0)

    default_file_idx = list(df.columns).index("file_name") if "file_name" in df.columns else min(1, len(df.columns) - 1)
    file_col = st.selectbox(
        "Noms des fichiers liés",
        options=list(df.columns),
        index=default_file_idx,
        help="Cellule avec un ou plusieurs noms (ex. doc.pdf ; image.png). Séparateurs : ; | ou retour à la ligne.",
    )

    path_opts = ["(aucune)"] + list(df.columns)
    path_idx = path_opts.index("path") if "path" in path_opts else 0
    path_col = st.selectbox(
        "Sous-dossiers sous la racine (optionnel)",
        options=path_opts,
        index=path_idx,
        help="Colonne listant des chemins **relatifs** au dossier racine (ex. archives/2024). "
        "Plusieurs dossiers : séparez par ; ou retour à la ligne. La recherche est **récursive** dans chacun.",
    )
    use_path_column = path_col != "(aucune)"

    optional = ["(aucune)"] + list(df.columns)
    summary_idx = optional.index("summary") if "summary" in optional else 0
    summary_col = st.selectbox("Résumé ou description", options=optional, index=summary_idx)

    excluded_for_meta = {title_col, file_col}
    if use_path_column:
        excluded_for_meta.add(path_col)
    default_meta = [c for c in df.columns if c not in excluded_for_meta]
    meta_cols = st.multiselect(
        "Autres métadonnées à afficher",
        options=list(df.columns),
        default=default_meta,
    )

    st.header("4. Recherche et filtres")
    query = st.text_input("Recherche (texte simple dans tout le tableau)")
    only_with_file = st.checkbox("Uniquement les notices avec un nom de fichier renseigné")

# ---------------------------------------------------------------------------
# Filtrage
# ---------------------------------------------------------------------------

mask = row_matches_query(df, query)
filtered_df = df[mask].copy()

if only_with_file:
    filtered_df = filtered_df[
        filtered_df[file_col].notna() & (filtered_df[file_col].astype(str).str.strip() != "")
    ]

if filtered_df.empty:
    st.warning("Aucune notice ne correspond aux critères actuels.")
    st.stop()

index_list = list(filtered_df.index)
labels = [
    build_record_label(filtered_df.loc[idx], title_col, pos)
    for pos, idx in enumerate(index_list, start=1)
]

if st.session_state.selected_index not in index_list:
    st.session_state.selected_index = index_list[0]

# ---------------------------------------------------------------------------
# Styles fiche « notice » (une fois les données chargées)
# ---------------------------------------------------------------------------

inject_notice_styles()

# ---------------------------------------------------------------------------
# Navigation entre notices
# ---------------------------------------------------------------------------

nav_a, nav_b, nav_c = st.columns([1, 1, 4])

with nav_a:
    if st.button("◀ Précédente", use_container_width=True, help="Notice précédente dans la liste filtrée"):
        cur = index_list.index(st.session_state.selected_index)
        if cur > 0:
            st.session_state.selected_index = index_list[cur - 1]

with nav_b:
    if st.button("Suivante ▶", use_container_width=True, help="Notice suivante dans la liste filtrée"):
        cur = index_list.index(st.session_state.selected_index)
        if cur < len(index_list) - 1:
            st.session_state.selected_index = index_list[cur + 1]

with nav_c:
    pick = st.selectbox(
        "Aller à une notice",
        options=labels,
        index=index_list.index(st.session_state.selected_index),
        help="Sélection directe dans les résultats du filtre actuel",
    )
    st.session_state.selected_index = index_list[labels.index(pick)]

selected_row = filtered_df.loc[st.session_state.selected_index]
position, total = get_notice_position(filtered_df, st.session_state.selected_index)

render_navigation_strip(position, total)

# ---------------------------------------------------------------------------
# Dossier des ressources : validité (pas d’indexation complète des médias au démarrage)
# ---------------------------------------------------------------------------

assets_dir_valid = False
assets_path: Path | None = None
if assets_dir.strip():
    assets_path = Path(assets_dir.strip()).expanduser()
    assets_dir_valid = assets_path.is_dir()

# ---------------------------------------------------------------------------
# Zone principale : fiche notice + document (fichier résolu à la sélection)
# ---------------------------------------------------------------------------

col_left, col_right = st.columns([1.12, 1.28], gap="large")

with col_left:
    render_notice_fiche(
        selected_row=selected_row,
        df_columns=list(df.columns),
        title_col=title_col,
        summary_col=summary_col,
        meta_cols=meta_cols,
    )

with col_right:
    render_document_panel(
        selected_row=selected_row,
        file_col=file_col,
        path_col=path_col,
        use_path_column=use_path_column,
        assets_dir=assets_dir,
        assets_path=assets_path,
        assets_dir_valid=assets_dir_valid,
        media_kind=media_kind,
        selection_key=st.session_state.selected_index,
    )

# ---------------------------------------------------------------------------
# Aperçu tabulaire (optionnel)
# ---------------------------------------------------------------------------

with st.expander("Voir le tableau filtré (aperçu)", expanded=False):
    render_filtered_preview(
        filtered_df,
        file_col=file_col,
        path_col=path_col,
        use_path_column=use_path_column,
        assets_path=assets_path,
        assets_dir_valid=assets_dir_valid,
        media_kind=media_kind,
    )

st.caption(
    "Sans colonne « chemins », la recherche porte sur toute l’arborescence sous la racine. "
    "Avec une colonne chemins, seuls les sous-dossiers indiqués sont parcourus (y compris leurs sous-dossiers)."
)
