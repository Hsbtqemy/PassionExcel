@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist "embed\python\python.exe" (
    echo Preparation du Python embarque ^(telechargement, ~25 Mo^)...
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0prepare_embed_python.ps1"
    if errorlevel 1 (
        echo.
        echo [Erreur] Python embarque requis pour compiler PassionExcel.iss ^(ligne embed\python\*^).
        echo.
        pause
        exit /b 1
    )
)

set "ISCC="
rem Chemin personnalise (optionnel) : definir INNO_SETUP_HOME vers le dossier contenant ISCC.exe
if defined INNO_SETUP_HOME if exist "%INNO_SETUP_HOME%\ISCC.exe" set "ISCC=%INNO_SETUP_HOME%\ISCC.exe"
if "%ISCC%"=="" if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if "%ISCC%"=="" if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
rem Install par utilisateur (winget / certains installeurs)
if "%ISCC%"=="" if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
rem Chemin enregistre dans le registre (Desinstaller un programme)
if "%ISCC%"=="" for /f "delims=" %%I in ('powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0find_iscc.ps1"') do set "ISCC=%%I"
rem Si ISCC est dans le PATH (apres install / session recente)
if "%ISCC%"=="" for /f "delims=" %%I in ('where iscc.exe 2^>nul') do set "ISCC=%%I" & goto :have_iscc
:have_iscc

if "%ISCC%"=="" (
    echo [Erreur] Inno Setup 6 introuvable ^(ISCC.exe^).
    echo.
    echo Installez Inno Setup 6, puis relancez ce script. Exemples :
    echo   winget install -e --id JRSoftware.InnoSetup
    echo   https://jrsoftware.org/isdl.php
    echo.
    echo Si Inno est installe ailleurs : definissez INNO_SETUP_HOME vers son dossier ^(celui qui contient ISCC.exe^).
    echo Diagnostic : nouvelle fenetre CMD puis   where iscc.exe
    echo   ou ouvrez le dossier d^'installation d^'Inno Setup 6 ^(voir Parametres - Applications^).
    echo.
    pause
    exit /b 1
)

if exist "%~dp0app_icon.png" (
    echo Generation de app_icon.ico depuis app_icon.png...
    "%~dp0embed\python\python.exe" -m pip install Pillow -q
    if errorlevel 1 (
        echo [Erreur] pip install Pillow a echoue.
        pause
        exit /b 1
    )
    "%~dp0embed\python\python.exe" "%~dp0png_to_ico.py"
    if errorlevel 1 (
        echo [Erreur] Conversion app_icon.png vers app_icon.ico echouee.
        pause
        exit /b 1
    )
)

echo Compilation avec : %ISCC%
"%ISCC%" "%~dp0PassionExcel.iss"
if errorlevel 1 (
    echo Echec de la compilation.
    pause
    exit /b 1
)

echo.
echo Installateur genere dans : %~dp0..\dist\
explorer "%~dp0..\dist" 2>nul
pause
