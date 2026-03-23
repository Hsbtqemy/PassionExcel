# Consultation documentaire (MVP)

Application **locale** en Python / Streamlit : les lignes d’un **CSV** ou d’un **Excel (.xlsx)** deviennent des **fiches lisibles**, avec ouverture des **fichiers associés** (PDF, images, audio, vidéo, ou téléchargement) stockés dans un **dossier sur votre machine**. Aucun dépôt cloud ni base de données.

## Prérequis

- **Python 3.11** ou plus récent  
- Fichiers tabulaires au format **CSV** ou **XLSX** (feuille au choix)

## Installation

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

## Lancement

```bash
streamlit run app.py
```

Le navigateur s’ouvre sur l’application (outil pensé pour des collègues non informaticiens : barre latérale pour la configuration, zone centrale pour la notice et le document).

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
├── passion_excel/         # Logique métier (sans UI)
│   ├── __init__.py
│   ├── loader.py          # Chargement CSV / XLSX
│   ├── files.py           # Résolution des chemins (racine puis sous-dossiers)
│   ├── search.py          # Recherche textuelle littérale
│   ├── notice_helpers.py  # Libellés et normalisation
│   └── display.py         # Affichage des médias
├── examples/
│   └── sample_notices.csv
├── requirements.txt
└── README.md
```

## Choix techniques (bref)

- **Streamlit** : interface web locale rapide à mettre en place, adaptée à un MVP de consultation.
- **pandas** : lecture tabulaire unifiée (CSV / Excel) et filtrage.
- **openpyxl** : moteur Excel pour `.xlsx` (standard avec pandas).
- **Résolution des fichiers** : d’abord `dossier_racine / nom_indiqué`, puis recherche récursive par nom de fichier ; **aucun contenu** de document n’est lu tant qu’une notice n’est pas affichée (seuls les tests d’existence et l’affichage chargent les médias).
- **Recherche** : sous-chaîne **sans expression régulière** (`regex=False`) pour éviter les pièges pour les utilisateurs SHS.
- **Sécurité minimale** : les chemins **absolus** dans le tableur sont ignorés pour le lien fichier ; seul le contenu sous le dossier racine est pris en compte.

## Feuille de route V1.1 (suggestions)

1. **Mémorisation des préférences** : enregistrer le dernier dossier racine et le mapping de colonnes (fichier local JSON ou `st.session_state` persistant selon besoin).
2. **Colonne « identifiant » configurable** : choisir quelle colonne sert de libellé secondaire au lieu du seul numéro d’ordre.
3. **Avertissement pour gros dossiers** : message si la recherche récursive pourrait être lente, ou limite de profondeur.
4. **Export** : exporter la liste filtrée en CSV depuis l’aperçu.
5. **Accessibilité** : thème contrasté, tailles de police, libellés de boutons encore plus explicites pour le public SHS.
