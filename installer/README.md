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
   - **Icône (optionnel)** : placez `installer\windows\app_icon.png` (PNG carré, idéalement ≥ 256 px). Au lancement, **`build.bat`** installe Pillow dans l’embed et exécute **`png_to_ico.py`** pour produire **`app_icon.ico`** (raccourcis Menu Démarrer / Bureau, assistant d’installation, désinstallation). Sans ce fichier, le comportement reste inchangé.
3. **Ou** double-cliquez sur **`build.bat`** : si `embed\python\` est absent, le script lance `prepare_embed_python.ps1` (téléchargement). Sans ce dossier, **Inno Setup échoue** sur la ligne `embed\python\*` (le compilateur exige que les fichiers sources existent).
4. Résultat : `installer\dist\PassionExcel_Setup_0.2.7.exe` (le numéro suit `#define MyAppVersion` dans `PassionExcel.iss`).

L’utilisateur final obtient une copie dans **`%LOCALAPPDATA%\PassionExcel`** (sans espace dans le nom du dossier) avec raccourcis ; **`run.bat`** utilisera le Python copié dans `python\` s’il n’a pas déjà Python 3.11+ sur le PATH.

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
- **Runner** : `windows-latest` — exécution de **`prepare_embed_python.ps1`** (télécharge Python embeddable dans `installer/windows/embed/python/`), puis **Chocolatey** installe **Inno Setup 6** et compilation de `PassionExcel.iss`.
- Pour un **tag** `vX.Y.Z`, la version dans le `.iss` est **remplacée** automatiquement avant compilation ; le workflow publie le **`.exe`** sur la release avec **`gh release upload`** (chemin absolu, pour éviter une release **sans binaire** à cause des globs Windows).
- **Paramètres dépôt** : **Settings → Actions → General → Workflow permissions** → cocher **Read and write permissions** (sinon `GITHUB_TOKEN` ne peut pas créer / mettre à jour les releases).
- Si une release est **vide** : ouvrir l’onglet **Actions**, vérifier que le job **Release (installateur Windows)** est **vert** ; en cas d’échec (Inno Setup, `app.py` manquant au build, etc.), corriger puis **repousser un nouveau tag** ou relancer le workflow.

Le paquet **macOS** (`.app` / DMG) et le script **`run.sh`** ne sont pas produits par cette CI : le `.sh` est déjà versionné à la racine ; le build Mac reste à faire sur une machine macOS (voir section macOS ci-dessus).

### Le `.exe` de la release est-il « standalone » ?

**Non** : c’est un **installateur Inno Setup**. Il copie l’application (dont **`PassionExcel.vbs`**, **`run.bat`**, Python embarqué si le build l’a inclus) sous **`%LOCALAPPDATA%\PassionExcel`**. Ce n’est pas un **seul** exécutable autonome type PyInstaller ; après installation, l’app tourne comme un projet Streamlit classique (console + navigateur).

### Dépannage Windows (message « impossible d’accéder au périphérique, au chemin… »)

Les raccourcis passent par **`wscript.exe`** et **`PassionExcel.vbs`** (plus fiable qu’un `.lnk` vers `run.bat` seul). L’installation va sous **`%LOCALAPPDATA%\PassionExcel`**. Si le problème persiste :

- Ouvrez l’explorateur, allez dans **`%LOCALAPPDATA%\PassionExcel`** (ou **`%LOCALAPPDATA%\Passion Excel`** si ancienne installation) et double-cliquez sur **`run.bat`**.
- Vérifiez qu’**aucun antivirus / stratégie** ne bloque **`powershell.exe`**, **`cmd.exe`** ou **`python.exe`** dans ce dossier.
- Si le dossier est sous **OneDrive** « fichiers en ligne uniquement », **téléchargez-le en local** avant de lancer l’appli.

## Désinstallation

- Windows : le désinstalleur supprime aussi **`python`** et **`.venv`** sous le dossier d’installation.
