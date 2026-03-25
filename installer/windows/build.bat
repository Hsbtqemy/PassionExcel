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
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"

if "%ISCC%"=="" (
    echo [Erreur] Inno Setup 6 introuvable.
    echo Installez-le depuis https://jrsoftware.org/isdl.php
    echo Puis relancez ce script.
    pause
    exit /b 1
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
