"""Chargement des tableurs CSV, Excel (XLSX) et OpenDocument (ODS, ODT) depuis upload ou chemin local."""

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


def _load_odt_first_table(source: bytes | Path) -> pd.DataFrame:
    """Charge le premier tableau d'un fichier ODT (texte) en structure tabulaire."""
    from odf import teletype, text
    from odf.opendocument import load
    from odf.table import Table, TableCell, TableRow

    if isinstance(source, bytes):
        doc = load(BytesIO(source))
    else:
        doc = load(str(source))

    tables = doc.getElementsByType(Table)
    if not tables:
        raise ValueError("Aucun tableau n’a été trouvé dans ce document ODT.")

    def _cell_text(cell: TableCell) -> str:
        paragraphs = cell.getElementsByType(text.P)
        if not paragraphs:
            return ""
        return "".join(teletype.extractText(p) for p in paragraphs)

    t = tables[0]
    rows_data: list[list[str]] = []
    for row in t.getElementsByType(TableRow):
        row_cells: list[str] = []
        for cell in row.getElementsByType(TableCell):
            row_cells.append(_cell_text(cell))
        rows_data.append(row_cells)

    if not rows_data:
        raise ValueError("Le premier tableau du document ODT est vide.")

    max_len = max(len(r) for r in rows_data)
    rows_data = [r + [""] * (max_len - len(r)) for r in rows_data]

    if len(rows_data) == 1:
        return pd.DataFrame([rows_data[0]])

    header = rows_data[0]
    body = rows_data[1:]
    return pd.DataFrame(body, columns=header)


def load_table_from_upload(
    file_bytes: bytes,
    file_name: str,
    sheet_name: str | None = None,
) -> pd.DataFrame:
    """Charge un CSV, XLSX, ODS ou ODT (premier tableau) à partir d'un fichier téléversé."""
    lower_name = file_name.lower()

    if lower_name.endswith(".csv"):
        return _read_csv_auto_separator(BytesIO(file_bytes))

    if lower_name.endswith(".xlsx"):
        return pd.read_excel(BytesIO(file_bytes), sheet_name=sheet_name, engine="openpyxl")

    if lower_name.endswith(".ods"):
        return pd.read_excel(BytesIO(file_bytes), sheet_name=sheet_name, engine="odf")

    if lower_name.endswith(".odt"):
        return _load_odt_first_table(file_bytes)

    raise ValueError("Format non pris en charge. Utiliser CSV, XLSX, ODS ou ODT.")


def list_table_sheets(file_bytes: bytes, file_name: str) -> list[str]:
    """Liste les feuilles d'un classeur (Excel ou ODS) ; ODT : une entrée factice."""
    lower_name = file_name.lower()

    if lower_name.endswith(".xlsx"):
        excel = pd.ExcelFile(BytesIO(file_bytes), engine="openpyxl")
        return list(excel.sheet_names)

    if lower_name.endswith(".ods"):
        excel = pd.ExcelFile(BytesIO(file_bytes), engine="odf")
        return list(excel.sheet_names)

    if lower_name.endswith(".odt"):
        return ["Premier tableau du document"]

    raise ValueError("Feuilles non applicables à ce format.")


def load_table_from_path(file_path: str, sheet_name: str | None = None) -> pd.DataFrame:
    """Charge un tableur depuis un chemin sur la machine qui exécute l'application."""
    path = Path(file_path)
    lower_name = path.name.lower()

    if lower_name.endswith(".csv"):
        return _read_csv_auto_separator(path)

    if lower_name.endswith(".xlsx"):
        return pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl")

    if lower_name.endswith(".ods"):
        return pd.read_excel(path, sheet_name=sheet_name, engine="odf")

    if lower_name.endswith(".odt"):
        return _load_odt_first_table(path)

    raise ValueError("Format non pris en charge. Utiliser CSV, XLSX, ODS ou ODT.")


def list_table_sheets_from_path(file_path: str) -> list[str]:
    """Liste les feuilles d'un fichier sur disque."""
    path = Path(file_path)
    lower_name = path.name.lower()

    if lower_name.endswith(".xlsx"):
        excel = pd.ExcelFile(path, engine="openpyxl")
        return list(excel.sheet_names)

    if lower_name.endswith(".ods"):
        excel = pd.ExcelFile(path, engine="odf")
        return list(excel.sheet_names)

    if lower_name.endswith(".odt"):
        return ["Premier tableau du document"]

    raise ValueError("Feuilles non applicables à ce format.")
