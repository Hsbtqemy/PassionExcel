"""Libellés de notices et utilitaires d'affichage (sans imposer une colonne « id »)."""

from __future__ import annotations

import pandas as pd


def normalize_value(value: object) -> str:
    """Convertit une valeur de cellule en texte lisible (vide si NaN)."""
    if pd.isna(value):
        return ""
    return str(value)


def build_record_label(row: pd.Series, title_col: str, position_in_list: int) -> str:
    """Construit un libellé court pour la liste : numéro + titre (pas de colonne id requise)."""
    title = normalize_value(row.get(title_col, "")).strip() or "(sans titre)"
    return f"{position_in_list}. {title}"


def get_notice_position(df: pd.DataFrame, selected_index: object) -> tuple[int, int]:
    """Position 1-based de la ligne sélectionnée parmi les lignes filtrées."""
    positions = list(df.index)
    if selected_index not in positions:
        return 1, len(positions)
    return positions.index(selected_index) + 1, len(positions)
