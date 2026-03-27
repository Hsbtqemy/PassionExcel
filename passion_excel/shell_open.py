"""Ouverture de dossiers locaux dans le gestionnaire de fichiers (Explorateur, Finder, etc.)."""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path


def open_folder(path: Path) -> tuple[bool, str]:
    """
    Ouvre un dossier dans l’explorateur système.
    Si `path` est un fichier, ouvre le dossier parent.
    Retourne (succès, message d’erreur éventuel).
    """
    try:
        p = path.expanduser().resolve()
        if not p.exists():
            return False, "Chemin introuvable."
        if p.is_file():
            p = p.parent
        if not p.is_dir():
            return False, "Ce n’est pas un dossier."
        system = platform.system()
        if system == "Windows":
            os.startfile(str(p))  # type: ignore[attr-defined]
        elif system == "Darwin":
            subprocess.Popen(["open", str(p)], start_new_session=True)
        else:
            subprocess.Popen(["xdg-open", str(p)], start_new_session=True)
        return True, ""
    except Exception as e:
        return False, str(e)
