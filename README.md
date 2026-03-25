# Consultation documentaire (MVP)

Application **locale** en Python / Streamlit : les lignes d’un **CSV** ou d’un **Excel (.xlsx)** deviennent des **fiches lisibles**, avec ouverture des **fichiers associés** (PDF, images, audio, vidéo, ou téléchargement) stockés dans un **dossier sur votre machine**. Pour une même notice, **PDF et images** peuvent s’afficher **l’un sous l’autre** (aperçu PDF puis galerie d’images avec sélecteur). Aucun dépôt cloud ni base de données.

## Utilisation simple (utilisateurs non techniques)

L’idée : **installer Python une fois**, puis lancer l’outil avec un **script** fourni — pas besoin de connaître la ligne de commande au quotidien.

### Python sur la machine (3.11 ou plus récent)

Le programme **détecte** d’abord un Python **déjà installé** (`python` / `python3`, et sous Windows le lanceur **`py -3`**). S’il est en **3.11+**, il est utilisé pour créer le dossier `.venv` et lancer Streamlit.

Si aucun Python adapté n’est trouvé, les lanceurs **`run.bat`** / **`run.sh`** cherchent un **Python embarqué** dans le dossier **`python/`** à côté de l’application (fourni par les installateurs après `prepare_embed_python`, voir `installer/README.md`).

| Système | Sans dossier `python/` embarqué |
|--------|----------------------------------|
| **Windows** | [python.org/downloads](https://www.python.org/downloads/) — cochez **« Add python.exe to PATH »**. |
| **macOS** | [python.org](https://www.python.org/downloads/) ou `brew install python`. |
| **Linux** | Paquets `python3` et `python3-venv`. |

Sans Python système **ni** copie embarquée, l’application ne peut pas démarrer.

### Lancer le programme

1. **Téléchargez ou clonez** ce dossier projet sur l’ordinateur (par ex. dézipper `PassionExcel` sur le Bureau).
2. **Windows** : double-cliquez sur **`run.bat`**.  
   - Si Windows demande une confirmation, autorisez l’exécution.  
   - La première fois, le script crée un dossier `.venv`, installe les bibliothèques, puis ouvre le navigateur.
3. **macOS / Linux** : ouvrez un terminal dans le dossier du projet, puis :
   ```bash
   chmod +x run.sh    # une seule fois, pour autoriser l’exécution
   ./run.sh
   ```
   Vous pouvez aussi faire glisser `run.sh` dans une fenêtre Terminal pour l’exécuter.

Pour **arrêter** l’application : fermez la fenêtre du terminal (Windows) ou faites **Ctrl+C** dans le terminal (Mac/Linux).

### Ce qu’il faut transmettre aux collègues

Envoyez-leur **tout le dossier du projet** (ou le dépôt GitHub en archive), pas seulement `app.py` : il leur faut `requirements.txt`, le dossier `passion_excel/`, et surtout **`run.bat`** / **`run.sh`**.

### Limites réalistes pour un public « lambda »

- Il faut **accepter d’installer Python** (comme pour beaucoup d’outils scientifiques). Embarquer Python dans un **seul** `.exe` « tout-en-un » est possible mais lourd pour Streamlit ; les scripts et installateurs ci-dessous restent l’approche pragmatique.
- Les **mises à jour** du programme : remplacer le dossier ou faire `git pull` si vous utilisez Git.

### Installateur Windows et paquet macOS (optionnel)

Pour distribuer un **assistant d’installation** (raccourcis, dossier d’installation propre) sans que l’utilisateur dézippe le dépôt à la main :

- Dossier **`installer/`** : script **Inno Setup** pour Windows (`.exe` généré) et script **`build_app.sh`** pour créer **`PassionExcel.app`** + **DMG** sur Mac.
- Instructions détaillées : **[installer/README.md](installer/README.md)**.

Ces installateurs **copient** l’application ; **Python reste à installer séparément** sur la machine cible.

## Prérequis

- **Python 3.11** ou plus récent  
- Fichiers tabulaires : **CSV**, **Excel (.xlsx)**, **LibreOffice Calc (.ods)**, **Writer (.odt**, premier tableau du document) — pour ODS/ODT le paquet **odfpy** est requis (voir `requirements.txt`).
- **Pillow** pour redimensionnement / vignettes des images (voir `requirements.txt`). Option **Pillow-SIMD** sous Linux : fichier séparé **`requirements-pillow-simd.txt`** (ne remplace pas `pillow` sous Windows / Python 3.12 sans build manuel).

## Installation (méthode manuelle, développeurs)

À la racine du projet :

```bash
python -m venv .venv
```

**Windows (PowerShell)** :

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**macOS / Linux** :

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

Après un **`git pull`** ou une mise à jour du dépôt, relancez **`pip install -r requirements.txt`** dans le même environnement virtuel pour récupérer les nouvelles dépendances.

## Lancement

**Méthode conseillée pour tout le monde** : `run.bat` (Windows) ou `./run.sh` (Mac/Linux), voir la section *Utilisation simple* ci-dessus.

**Méthode manuelle** :

```bash
streamlit run app.py
```

Le navigateur s’ouvre sur l’application (barre latérale pour la configuration, zone centrale pour la notice et le document).

## Fichier d’exemple

Un CSV minimal est fourni : `examples/sample_notices.csv`. Indiquez un dossier racine où vous placerez (ou non) des fichiers nommés comme dans la colonne « fichier lié » pour tester l’affichage.

## Format de données conseillé

Exemple de colonnes (les noms peuvent être libres grâce au mapping dans l’interface) :

| id | title | author | year | summary | file_name |
|----|-------|--------|------|---------|-----------|
| 1 | Titre | Auteur | 2024 | Texte | document.pdf |

La colonne **identifiant** n’est pas obligatoire : les notices sont distinguées par un numéro d’ordre dans la liste filtrée.

## Arborescence du projet recommandée

```text
PassionExcel/
├── app.py                 # Point d’entrée Streamlit
├── run.bat                # Lancement simple sous Windows
├── run.sh                 # Lancement simple sous macOS / Linux
├── installer/             # Scripts Inno Setup (Windows) et .app / DMG (Mac)
├── passion_excel/
│   ├── __init__.py
│   ├── loader.py          # Chargement CSV / XLSX / ODS / ODT
│   ├── files.py           # Résolution des chemins (racine, sous-dossiers, types média)
│   ├── search.py          # Recherche textuelle littérale
│   ├── notice_helpers.py  # Libellés et normalisation
│   ├── display.py         # PDF (PyMuPDF), images, cache, galerie
│   ├── ui_notice.py       # Fiche notice / panneau documents / styles
│   └── folder_picker.py   # Dialogue fichier local (Tk, hors Streamlit Cloud)
├── examples/
│   └── sample_notices.csv
├── requirements.txt
├── requirements-pillow-simd.txt   # Optionnel (Pillow-SIMD, surtout Linux)
└── README.md
```

## Choix techniques (bref)

- **Streamlit** : interface web locale rapide à mettre en place, adaptée à un MVP de consultation ; **fragment** sur le panneau documents pour limiter les reruns inutiles.
- **pandas** : lecture tabulaire unifiée (CSV / Excel) et filtrage.
- **openpyxl** : moteur Excel pour `.xlsx` (standard avec pandas).
- **Résolution des fichiers** : d’abord `dossier_racine / nom_indiqué`, puis recherche récursive par nom de fichier ; **aucun contenu** de document n’est lu tant qu’une notice n’est pas affichée (seuls les tests d’existence et l’affichage chargent les médias).
- **PDF** : aperçu via **PyMuPDF** (raster JPEG) + lecteur `st.pdf` en secours ; cache des pages et pagination « charger plus ».
- **Images** : **Pillow** (redimensionnement, vignettes, JPEG) ; `JPEG draft` et cache pour limiter le coût CPU.
- **Recherche** : sous-chaîne **sans expression régulière** (`regex=False`) pour éviter les pièges pour les utilisateurs SHS.
- **Sécurité minimale** : les chemins **absolus** dans le tableur sont ignorés pour le lien fichier ; seul le contenu sous le dossier racine est pris en compte.

## Déploiement Streamlit Cloud (optionnel)

Le dépôt peut être connecté à **[Streamlit Community Cloud](https://streamlit.io/cloud)** : fichier principal **`app.py`**, dépendances **`requirements.txt`**, Python **3.11+**. **Aucun secret** n’est requis par défaut. En revanche, l’app est conçue pour des **chemins locaux** et un **dossier médias** sur le disque : sur le cloud, seul le **téléversement** du tableur est vraiment adapté ; l’affichage des fichiers liés par chemin local ne fonctionne pas comme sur un poste de travail.

## Installateur Windows (.exe)

Voir **`installer/README.md`** : compilation locale avec **Inno Setup 6** et **`installer/windows/build.bat`**. Sur **GitHub**, le workflow **`.github/workflows/release-installer.yml`** compile l’installateur et attache le **`.exe`** à une **release** lorsque vous poussez un **tag** `v*` (ex. `v0.2.3`).

Le script **`run.sh`** n’a pas de phase de build : il est fourni tel quel pour macOS / Linux.

## Feuille de route V1.1 (suggestions)

1. **Mémorisation des préférences** : enregistrer le dernier dossier racine et le mapping de colonnes (fichier local JSON ou `st.session_state` persistant selon besoin).
2. **Colonne « identifiant » configurable** : choisir quelle colonne sert de libellé secondaire au lieu du seul numéro d’ordre.
3. **Avertissement pour gros dossiers** : message si la recherche récursive pourrait être lente, ou limite de profondeur.
4. **Export** : exporter la liste filtrée en CSV depuis l’aperçu.
5. **Accessibilité** : thème contrasté, tailles de police, libellés de boutons encore plus explicites pour le public SHS.
