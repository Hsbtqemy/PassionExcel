"""Sélecteurs natifs (tkinter) pour usage local — dossier ou fichier tableur."""

from __future__ import annotations


class TkNotAvailableError(Exception):
    """tkinter absent (Python minimal) ou environnement sans interface graphique."""


def pick_folder(title: str = "Choisir un dossier") -> str | None:
    """Ouvre la boîte de dialogue système pour un dossier. ``None`` si annulation."""
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError as e:
        raise TkNotAvailableError(
            "Le module tkinter n’est pas disponible. Utilisez le champ texte ou installez Python avec les composants Tcl/Tk.",
        ) from e

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        root.lift()
        root.focus_force()
    except Exception:
        pass
    try:
        path = filedialog.askdirectory(master=root, title=title, mustexist=True)
    finally:
        try:
            root.destroy()
        except Exception:
            pass

    return path if path else None


def pick_table_file(title: str = "Choisir un tableur") -> str | None:
    """Ouvre la boîte de dialogue pour un fichier CSV ou XLSX. ``None`` si annulation."""
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError as e:
        raise TkNotAvailableError(
            "Le module tkinter n’est pas disponible. Utilisez le champ texte ou installez Python avec les composants Tcl/Tk.",
        ) from e

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        root.lift()
        root.focus_force()
    except Exception:
        pass
    try:
        path = filedialog.askopenfilename(
            master=root,
            title=title,
            filetypes=[
                ("CSV ou Excel", "*.csv *.xlsx"),
                ("CSV", "*.csv"),
                ("Excel", "*.xlsx"),
                ("Tous les fichiers", "*.*"),
            ],
        )
    finally:
        try:
            root.destroy()
        except Exception:
            pass

    return path if path else None
