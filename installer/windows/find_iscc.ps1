# Retourne le chemin complet de ISCC.exe si Inno Setup 6 est enregistre dans Desinstaller un programme.
$ErrorActionPreference = 'SilentlyContinue'
$hives = @(
    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*'
)
foreach ($pattern in $hives) {
    Get-ItemProperty $pattern | Where-Object {
        $_.DisplayName -match '^Inno Setup 6' -and $_.InstallLocation
    } | ForEach-Object {
        $exe = Join-Path $_.InstallLocation.TrimEnd('\') 'ISCC.exe'
        if (Test-Path -LiteralPath $exe) {
            Write-Output $exe
            exit 0
        }
    }
}
