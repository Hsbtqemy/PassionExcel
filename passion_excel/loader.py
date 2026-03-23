"""Chargement des tableurs CSV et Excel (XLSX) depuis upload ou chemin local."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd


def _read_csv_auto_separator(source: str | Path | BinaryIO) -> pd.DataFrame:
    """Lit un CSV en détectant le séparateur (virgule, point-virgule, tabulation, etc.).

    Utilise le moteur Python de pandas avec ``sep=None`` (inférence via le module ``csv``).
    En cas d'échec de l'inférence, repli sur la virgule par défaut.
    """
    try:
        return pd.read_csv(source, sep=None, engine="python")
    except Exception:
        if hasattr(source, "seek"):
            source.seek(0)
        return pd.read_csv(source)


def load_table_from_upload(
    file_bytes: bytes,
    file_name: str,
    sheet_name: str | None = None,
) -> pd.DataFrame:
    """Charge un CSV ou XLSX à partir d'un fichier téléversé."""
    lower_name = file_name.lower()

    if lower_name.endswith(".csv"):
        return _read_csv_auto_separator(BytesIO(file_bytes))

    if lower_name.endswith(".xlsx"):
        return pd.read_excel(BytesIO(file_bytes), sheet_name=sheet_name, engine="openpyxl")

    raise ValueError("Format non pris en charge. Utiliser un fichier CSV ou XLSX.")


def list_excel_sheets(file_bytes: bytes) -> list[str]:
    """Liste les feuilles d'un classeur Excel en mémoire."""
    excel = pd.ExcelFile(BytesIO(file_bytes), engine="openpyxl")
    return list(excel.sheet_names)


def load_table_from_path(file_path: str, sheet_name: str | None = None) -> pd.DataFrame:
    """Charge un CSV ou XLSX depuis un chemin sur la machine qui exécute l'application."""
    path = Path(file_path)
    lower_name = path.name.lower()

    if lower_name.endswith(".csv"):
        return _read_csv_auto_separator(path)

    if lower_name.endswith(".xlsx"):
        return pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl")

    raise ValueError("Format non pris en charge. Utiliser un fichier CSV ou XLSX.")


def list_excel_sheets_from_path(file_path: str) -> list[str]:
    """Liste les feuilles d'un fichier Excel sur disque."""
    excel = pd.ExcelFile(file_path, engine="openpyxl")
    return list(excel.sheet_names)
