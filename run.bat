@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo === Consultation documentaire ===
echo.

REM Ordre : Python systeme (PATH, 3.11+) ^> py -3 ^> python embarque (dossier .\python\)
set "PY_EXE="
python -c "import sys; exit(0 if sys.version_info>=(3,11) else 1)" 2>nul && set "PY_EXE=python"
if not defined PY_EXE (
  where py >nul 2>&1 && py -3 -c "import sys; exit(0 if sys.version_info>=(3,11) else 1)" 2>nul && set "PY_EXE=py -3"
)
if not defined PY_EXE (
  if exist "%~dp0python\python.exe" (
    "%~dp0python\python.exe" -c "import sys; exit(0 if sys.version_info>=(3,11) else 1)" 2>nul && set "PY_EXE=%~dp0python\python.exe"
  )
)

if not defined PY_EXE (
    echo [Erreur] Python 3.11 ou plus recent est requis.
    echo.
    echo - Installez Python depuis https://www.python.org/downloads/ ^(cochez "Add to PATH"^)
    echo - Ou placez une distribution embarquee dans le dossier : %~dp0python\
    echo.
    pause
    exit /b 1
)

echo Python utilise : !PY_EXE!
echo.

if not exist ".venv\" (
    echo Creation de l'environnement virtuel local...
    !PY_EXE! -m venv .venv
    if errorlevel 1 (
        echo [Erreur] Impossible de creer l'environnement virtuel.
        pause
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"

echo Installation ou mise a jour des dependances...
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
pip install "streamlit[pdf]>=1.55,<2"
if errorlevel 1 (
    echo [Erreur] pip install a echoue.
    pause
    exit /b 1
)

echo.
echo Lancement de l'application. Le navigateur va s'ouvrir.
echo Fermez la fenetre noire pour arreter le programme.
echo.
python -m streamlit run app.py

if errorlevel 1 (
    echo.
    echo [Erreur] Le lancement a echoue.
    pause
)
