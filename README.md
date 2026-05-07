# Consultation documentaire (MVP)

Application **locale** en Python / Streamlit : les lignes d’un **CSV** ou d’un **Excel (.xlsx)** deviennent des **fiches lisibles**, avec accès aux **fichiers associés** (PDF, images, audio, vidéo, ou téléchargement) stockés dans un **dossier sur votre machine**. L’aperçu PDF / galerie d’images dans l’app est **sur demande** ; des **liens locaux** ouvrent les fichiers ou dossiers avec les applications du système. Aucun dépôt cloud ni base de données.

## Utilisation simple (utilisateurs non techniques)

L’idée : **télécharger l’installateur** depuis la page Releases GitHub, l’exécuter, puis lancer l’outil — **Python n’a pas besoin d’être installé sur la machine**.

### Installateurs prêts à l’emploi (releases GitHub)

| Système | Fichier à télécharger | Python requis ? |
|---|---|---|
| **Windows** | `PassionExcel_Setup_X.Y.Z.exe` | Non — embarqué |
| **macOS** | `PassionExcel_mac_X.Y.Z.dmg` | Non — embarqué dans le `.app` |

> **macOS — premier lancement :** l’application n’est pas signée par Apple. macOS peut la bloquer ; faites **clic droit → Ouvrir** (ou passez par Réglages Système → Confidentialité → « Ouvrir quand même »).

### Python sur la machine (méthode alternative, sans installateur)

Si vous préférez ne pas utiliser les installateurs, les lanceurs **`run.bat`** / **`run.sh`** détectent Python automatiquement : d’abord un Python **déjà installé** sur le système (`python` / `python3`, et sous Windows le lanceur **`py -3`** en 3.11+), sinon un **Python embarqué** dans le dossier **`python/`** à côté de l’application.

| Système | Sans Python embarqué |
|--------|----------------------|
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

- Les **installateurs embarquent Python** : aucune installation préalable requise. En revanche, sous macOS, l’absence de signature Apple impose un contournement Gatekeeper au premier lancement.
- Les **mises à jour** du programme : télécharger le nouvel installateur depuis les releases GitHub, ou faire `git pull` si vous utilisez Git.

### Installateur Windows et paquet macOS (optionnel)

Pour distribuer un **assistant d’installation** (raccourcis, dossier d’installation propre) sans que l’utilisateur dézippe le dépôt à la main :

- Dossier **`installer/`** : script **Inno Setup** pour Windows (`.exe` généré) et script **`build_app.sh`** pour créer **`PassionExcel.app`** + **DMG** sur Mac.
- Instructions détaillées : **[installer/README.md](installer/README.md)**.

**À bien comprendre pour Windows :** le fichier **`PassionExcel_Setup_….exe`** sur la **release GitHub** n’est **pas** une application « **standalone** » au sens d’un **seul** `.exe` qui contiendrait tout (comme certains outils packagés avec PyInstaller). C’est un **installateur** classique : il **décompresse** l’appli, **`run.bat`**, un **Python embarqué** (build CI), etc. dans **`%LOCALAPPDATA%\PassionExcel`**, puis vous lancez l’outil via le **raccourci** ou **`run.bat`** dans ce dossier. Ce n’est **pas** un binaire unique sans installation.

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
│   ├── shell_open.py      # Ouvrir un dossier dans l’explorateur (OS)
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
- **Résolution des fichiers** : d’abord `dossier_racine / nom_indiqué`, puis recherche récursive par nom de fichier. **Panneau documents** : liens `file://` par fichier, ouverture du **dossier racine** ou du **dossier parent** dans l’explorateur ; aperçu PDF / galerie **après** boutons « Charger PDF » / « Charger images ».
- **PDF** : par défaut **une page à la fois** (curseur) ; option **défilement continu** ; lien **ouvrir dans une nouvelle fenêtre** (lecteur système via `file://`) ; lecteur `st.pdf` en dernier recours si PyMuPDF indisponible.
- **Images** : **Pillow** (redimensionnement, vignettes, JPEG) ; **orientation EXIF** appliquée (`exif_transpose`) ; ordre d’affichage défini par le tri des chemins résolus (voir `files.py`). Au-delà d’un seuil (~18 images), la **grille de vignettes** est chargée **sur demande** pour éviter de décoder des dizaines de fichiers à chaque interaction.
- **Recherche** : sous-chaîne **sans expression régulière** (`regex=False`) pour éviter les pièges pour les utilisateurs SHS.
- **Sécurité minimale** : les chemins **absolus** dans le tableur sont ignorés pour le lien fichier ; seul le contenu sous le dossier racine est pris en compte.

## Déploiement Streamlit Cloud (optionnel)

Le dépôt peut être connecté à **[Streamlit Community Cloud](https://streamlit.io/cloud)** : fichier principal **`app.py`**, dépendances **`requirements.txt`**, Python **3.11+**. **Aucun secret** n’est requis par défaut. En revanche, l’app est conçue pour des **chemins locaux** et un **dossier médias** sur le disque : sur le cloud, seul le **téléversement** du tableur est vraiment adapté ; l’affichage des fichiers liés par chemin local ne fonctionne pas comme sur un poste de travail.

## Installateurs (Windows et macOS)

Voir **`installer/README.md`** pour la compilation locale.

Sur **GitHub**, deux workflows publient automatiquement les installateurs sur une **release** lorsque vous poussez un **tag** `v*` (ex. `v0.2.7`) :

| Workflow | Fichier produit | Python |
|---|---|---|
| `release-installer.yml` | `PassionExcel_Setup_X.Y.Z.exe` (Inno Setup) | Embarqué via `prepare_embed_python.ps1` |
| `release-installer-mac.yml` | `PassionExcel_mac_X.Y.Z.dmg` (`.app`) | Embarqué via `prepare_embed_python.sh` |

Les deux workflows tournent en parallèle sur le même tag et publient leurs fichiers sur la même release GitHub.

## Feuille de route V1.1 (suggestions)

1. **Mémorisation des préférences** : enregistrer le dernier dossier racine et le mapping de colonnes (fichier local JSON ou `st.session_state` persistant selon besoin).
2. **Colonne « identifiant » configurable** : choisir quelle colonne sert de libellé secondaire au lieu du seul numéro d’ordre.
3. **Avertissement pour gros dossiers** : message si la recherche récursive pourrait être lente, ou limite de profondeur.
4. **Export** : exporter la liste filtrée en CSV depuis l’aperçu.
5. **Accessibilité** : thème contrasté, tailles de police, libellés de boutons encore plus explicites pour le public SHS.
