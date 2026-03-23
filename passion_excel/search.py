"""Recherche textuelle simple (littérale, sans regex) dans le tableau."""

from __future__ import annotations

import pandas as pd


def row_matches_query(df: pd.DataFrame, query: str) -> pd.Series:
    """Retourne un masque : lignes dont au moins une cellule contient la sous-chaîne ``query``."""
    if not query.strip():
        return pd.Series([True] * len(df), index=df.index)

    # regex=False : recherche « naïve », adaptée aux utilisateurs non techniques
    return df.astype(str).apply(
        lambda col: col.str.contains(query, case=False, na=False, regex=False),
    ).any(axis=1)
