"""
Application Streamlit : consultation de notices à partir d'un tableur et de fichiers locaux.

Lancer : streamlit run app.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from passion_excel.loader import (
    list_excel_sheets,
    list_excel_sheets_from_path,
    load_table_from_path,
    load_table_from_upload,
)
from passion_excel.notice_helpers import (
    build_record_label,
    get_notice_position,
)
from passion_excel.search import row_matches_query
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
def _cached_list_sheets_upload(file_bytes: bytes) -> list[str]:
    return list_excel_sheets(file_bytes)


@st.cache_data(show_spinner=False)
def _cached_load_path(table_path: str, sheet_name: str | None) -> pd.DataFrame:
    return load_table_from_path(table_path, sheet_name)


@st.cache_data(show_spinner=False)
def _cached_list_sheets_path(table_path: str) -> list[str]:
    return list_excel_sheets_from_path(table_path)


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
    table_path = ""

    if source_mode == "Téléverser un fichier":
        uploaded_file = st.file_uploader(
            "Choisir un CSV ou un fichier Excel (.xlsx)",
            type=["csv", "xlsx"],
        )
    else:
        table_path = st.text_input(
            "Chemin complet du tableur",
            placeholder=r"Ex. C:\Corpus\notices.xlsx",
        )

    st.header("2. Dossier des documents liés")
    assets_dir = st.text_input(
        "Dossier racine contenant les fichiers",
        placeholder=r"Ex. C:\Corpus\documents",
        help="Les noms dans le tableur sont cherchés d’abord à la racine, puis dans les sous-dossiers.",
    )

    st.caption(
        "Indiquez plutôt un **nom de fichier** dans le tableur (ex. `article.pdf`) qu’un chemin absolu."
    )

# ---------------------------------------------------------------------------
# Chargement du tableur
# ---------------------------------------------------------------------------

try:
    df: pd.DataFrame | None = None
    sheet_name: str | None = None

    if source_mode == "Téléverser un fichier":
        if uploaded_file is None:
            st.info("Chargez un fichier CSV ou Excel (.xlsx) pour commencer.")
            st.stop()

        file_bytes = uploaded_file.getvalue()
        lower_name = uploaded_file.name.lower()

        if lower_name.endswith(".xlsx"):
            sheets = _cached_list_sheets_upload(file_bytes)
            sheet_name = st.sidebar.selectbox("Feuille Excel", sheets, key="sheet_upload")

        df = _cached_load_upload(file_bytes, uploaded_file.name, sheet_name)

    else:
        if not table_path.strip():
            st.info("Indiquez le chemin du fichier CSV ou Excel sur cet ordinateur.")
            st.stop()

        path = Path(table_path.strip())
        if not path.is_file():
            st.error("Ce chemin n’est pas un fichier valide ou le fichier est introuvable.")
            st.stop()

        lower_name = path.name.lower()
        if lower_name.endswith(".xlsx"):
            sheets = _cached_list_sheets_path(table_path.strip())
            sheet_name = st.sidebar.selectbox("Feuille Excel", sheets, key="sheet_path")

        df = _cached_load_path(table_path.strip(), sheet_name)

except Exception as exc:
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
    file_col = st.selectbox("Nom du fichier lié", options=list(df.columns), index=default_file_idx)

    optional = ["(aucune)"] + list(df.columns)
    summary_idx = optional.index("summary") if "summary" in optional else 0
    summary_col = st.selectbox("Résumé ou description", options=optional, index=summary_idx)

    default_meta = [c for c in df.columns if c not in {title_col, file_col}]
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
        assets_dir=assets_dir,
        assets_path=assets_path,
        assets_dir_valid=assets_dir_valid,
    )

# ---------------------------------------------------------------------------
# Aperçu tabulaire (optionnel)
# ---------------------------------------------------------------------------

with st.expander("Voir le tableau filtré (aperçu)", expanded=False):
    render_filtered_preview(
        filtered_df,
        file_col=file_col,
        assets_path=assets_path,
        assets_dir_valid=assets_dir_valid,
    )

st.caption(
    "Astuce : placez les fichiers sous le dossier racine ou dans des sous-dossiers ; "
    "le programme cherche d’abord à la racine, puis par nom de fichier."
)
