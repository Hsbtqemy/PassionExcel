"""Génère app_icon.ico à partir de app_icon.png (même dossier). Appelé avant ISCC si le PNG est présent."""
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    here = Path(__file__).resolve().parent
    png = here / "app_icon.png"
    ico = here / "app_icon.ico"
    if not png.is_file():
        return 0
    try:
        from PIL import Image
    except ImportError:
        print("Pillow requis : pip install Pillow", file=sys.stderr)
        return 1
    im = Image.open(png).convert("RGBA")
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    im.save(ico, format="ICO", sizes=sizes)
    print(f"OK : {ico}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
