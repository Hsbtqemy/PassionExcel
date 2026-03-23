# Télécharge la distribution « embeddable » officielle (Windows amd64), active pip, pour inclusion dans l'installateur.
# Exécuter depuis PowerShell :  powershell -ExecutionPolicy Bypass -File .\prepare_embed_python.ps1

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Version = "3.12.7"
$EmbedName = "python-$Version-embed-amd64.zip"
$Url = "https://www.python.org/ftp/python/$Version/$EmbedName"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Target = Join-Path $Root "embed\python"
$ZipPath = Join-Path $env:TEMP "pe-embed-$Version.zip"

Write-Host "→ Téléchargement : $Url"
Invoke-WebRequest -Uri $Url -OutFile $ZipPath -UseBasicParsing

if (Test-Path $Target) { Remove-Item -Recurse -Force $Target }
New-Item -ItemType Directory -Path $Target | Out-Null

Write-Host "→ Extraction vers $Target"
Expand-Archive -LiteralPath $ZipPath -DestinationPath $Target -Force
Remove-Item $ZipPath -Force

# Activer import site (nécessaire pour pip et venv)
$Pth = Get-ChildItem -Path $Target -Filter "python*._pth" | Select-Object -First 1
if (-not $Pth) { throw "Fichier ._pth introuvable après extraction." }
$lines = Get-Content $Pth.FullName
$out = @()
foreach ($line in $lines) {
    if ($line -match '^#\s*import site') {
        $out += 'import site'
    } else {
        $out += $line
    }
}
if ($out -notcontains 'import site') { $out += 'import site' }
$enc = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllLines($Pth.FullName, $out, $enc)

$PyExe = Join-Path $Target "python.exe"
$GetPip = Join-Path $env:TEMP "get-pip-pe.py"
Write-Host "→ Installation de pip"
Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $GetPip -UseBasicParsing
& $PyExe $GetPip --no-warn-script-location
Remove-Item $GetPip -Force -ErrorAction SilentlyContinue

Write-Host "→ OK. Python embarqué prêt : $PyExe"
& $PyExe -c "import sys; print('Version:', sys.version)"
