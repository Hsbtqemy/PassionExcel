# Installateurs Windows et macOS

## Principe

- **`run.bat`** / **`run.sh`** (à la racine du projet) choisissent **automatiquement** l’interpréteur :
  1. **Python système** sur le `PATH` si version **≥ 3.11** (`python`, puis `py -3` sous Windows),
  2. sinon **Python embarqué** dans le dossier **`python/`** à côté des scripts (`python\python.exe` sous Windows, `python/bin/python3` sous macOS/Linux).
- Les installateurs **copient** l’application et, si vous avez lancé les scripts de préparation, **un Python complet** dans `{app}\python` (Windows) ou `PassionExcel.app/Contents/Resources/python` (Mac).

Les dossiers **`installer/windows/embed/`** et **`installer/mac/embed/`** sont **ignorés par Git** (trop volumineux) : ils sont générés **avant** de compiler l’installateur ou le `.app`.

---

## Windows (Inno Setup + Python embarqué)

1. Installez **[Inno Setup 6](https://jrsoftware.org/isinfo.php)**.
2. (Optionnel mais recommandé) Téléchargez et préparez Python embarqué :
   ```powershell
   cd installer\windows
   powershell -ExecutionPolicy Bypass -File .\prepare_embed_python.ps1
   ```
   Cela crée `embed\python\` avec la distribution **embeddable** officielle (amd64), **pip** inclus.
3. **Ou** double-cliquez sur **`build.bat`** : si `embed\python\` est absent, le script lance `prepare_embed_python.ps1` (téléchargement) ; en cas d’échec, l’installateur est quand même produit **sans** Python embarqué.
4. Résultat : `installer\dist\PassionExcel_Setup_0.2.0.exe` (le numéro suit `#define MyAppVersion` dans `PassionExcel.iss`).

L’utilisateur final obtient une copie dans `%LOCALAPPDATA%\Passion Excel` avec raccourcis ; **`run.bat`** utilisera le Python copié dans `python\` s’il n’a pas déjà Python 3.11+ sur le PATH.

---

## macOS (.app + DMG + Python embarqué)

1. Sur un Mac, rendez les scripts exécutables :
   ```bash
   chmod +x installer/mac/prepare_embed_python.sh installer/mac/build_app.sh installer/mac/PassionExcel
   ```
2. **`build_app.sh`** appelle automatiquement **`prepare_embed_python.sh`** si `embed/python/` est absent (téléchargement depuis [python-build-standalone](https://github.com/astral-sh/python-build-standalone/releases), adapté **arm64** ou **x86_64**).
3. Résultat : `installer/mac/dist/PassionExcel.app` et un **DMG** si `hdiutil` est disponible.

Le lanceur **`PassionExcel`** préfère **`python3` / `python`** système (≥ 3.11), sinon le binaire embarqué dans **`Contents/Resources/python/`**.

Si l’URL de téléchargement change (nouvelle release), éditez **`TAG`**, **`PYVER`** et le nom de fichier dans `prepare_embed_python.sh`.

---

## Développement sans installateur

Clone du dépôt : placez un Python embarqué **à la racine** dans `./python/` (même structure que ci-dessus) **ou** installez Python 3.11+ classiquement. Puis **`run.bat`** / **`run.sh`**.

---

## CI GitHub (installateur Windows)

**Rappel :** un **tag Git** pointe toujours vers un **commit** : dans l’historique, « sur le tag » il n’y a que le **code source** (aucun `.exe` n’est commité — et ce n’est pas souhaitable). Sur la **page Release** GitHub, les liens **Source code (zip / tar.gz)** sont générés automatiquement à partir de ce commit.

Le workflow ci-dessous **construit** l’installateur **à partir** de ce code sur un runner Windows, puis **ajoute** le fichier `PassionExcel_Setup_….exe` comme **asset** de la même release (en plus des archives source).

Le dépôt inclut **`.github/workflows/release-installer.yml`** :

- **Déclenchement** : push d’un **tag** `v*` (ex. `v0.2.0`) ou exécution manuelle (**Actions → Release (installateur Windows) → Run workflow**).
- **Runner** : `windows-latest`, **Chocolatey** installe **Inno Setup 6**, puis compilation de `PassionExcel.iss` (sans Python embarqué dans `embed/` sauf si vous adaptez le workflow).
- Pour un **tag** `vX.Y.Z`, la version dans le `.iss` est **remplacée** automatiquement avant compilation ; une **release GitHub** est créée avec le **`.exe`** en pièce jointe.

Le paquet **macOS** (`.app` / DMG) et le script **`run.sh`** ne sont pas produits par cette CI : le `.sh` est déjà versionné à la racine ; le build Mac reste à faire sur une machine macOS (voir section macOS ci-dessus).

## Désinstallation

- Windows : le désinstalleur supprime aussi **`python`** et **`.venv`** sous le dossier d’installation.
