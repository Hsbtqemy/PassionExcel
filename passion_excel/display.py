"""Affichage des médias et téléchargement pour les types non prévisualisés."""

from __future__ import annotations

import mimetypes
from pathlib import Path

import streamlit as st


def display_linked_file(file_path: Path, *, show_filename_header: bool = True) -> None:
    """Affiche ou propose le téléchargement selon l'extension (lecture du fichier à l'appel)."""
    suffix = file_path.suffix.lower()
    mime_type, _ = mimetypes.guess_type(str(file_path))

    if show_filename_header:
        st.write(f"**Fichier trouvé** : `{file_path.name}`")
        st.caption(str(file_path))

    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}:
        st.image(file_path, use_container_width=True)
        return

    if suffix == ".pdf":
        st.pdf(str(file_path), height="stretch")
        return

    if suffix in {".mp3", ".wav", ".m4a", ".ogg", ".flac"}:
        st.audio(str(file_path))
        return

    if suffix in {".mp4", ".mov", ".webm", ".mkv"}:
        st.video(str(file_path))
        return

    if suffix == ".odt":
        mime_type = mime_type or "application/vnd.oasis.opendocument.text"
        with open(file_path, "rb") as f:
            st.download_button(
                label="Télécharger le document ODT (LibreOffice)",
                data=f.read(),
                file_name=file_path.name,
                mime=mime_type,
                use_container_width=True,
            )
        return

    with open(file_path, "rb") as f:
        st.download_button(
            label="Télécharger le fichier",
            data=f.read(),
            file_name=file_path.name,
            mime=mime_type or "application/octet-stream",
            use_container_width=True,
        )
