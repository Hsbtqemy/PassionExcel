; Installateur Windows — compiler avec Inno Setup 6+ (Unicode)
; Avant compilation : executer prepare_embed_python.ps1 pour inclure Python embarque (optionnel mais recommande).
; Icône optionnelle : placer app_icon.png puis lancer png_to_ico.py (génère app_icon.ico à côté).

#if FileExists("app_icon.ico")
#define HaveAppIcon
#endif

#define MyAppName "Passion Excel"
#define MyAppVersion "0.2.9"
; Dossier sans espace (evite erreurs Windows sur raccourcis / chemins).
#define MyInstallDirName "PassionExcel"
#define MyAppPublisher "Passion Excel"
#define MyAppURL "https://github.com/Hsbtqemy/PassionExcel"

[Setup]
AppId={{B4E8C2A1-7F3D-4E91-9C0A-1D2E3F4A5B6C}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\{#MyInstallDirName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=PassionExcel_Setup_{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
#ifdef HaveAppIcon
SetupIconFile=app_icon.ico
UninstallDisplayIcon={app}\app_icon.ico
#else
UninstallDisplayIcon={sys}\shell32.dll
#endif
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le Bureau"; GroupDescription: "Raccourcis :"; Flags: unchecked

[Files]
Source: "..\..\app.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\requirements-pillow-simd.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\run.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\PassionExcel.vbs"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\run.sh"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\passion_excel\*"; DestDir: "{app}\passion_excel"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\examples\*"; DestDir: "{app}\examples"; Flags: ignoreversion recursesubdirs createallsubdirs
; Python embarque (present si prepare_embed_python.ps1 a ete execute)
Source: "embed\python\*"; DestDir: "{app}\python"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: DirEmbedPython
#ifdef HaveAppIcon
Source: "app_icon.ico"; DestDir: "{app}"; Flags: ignoreversion
#endif

; Raccourcis : wscript.exe + PassionExcel.vbs (lance cmd avec bon repertoire ; plus fiable que .lnk -> .bat)

[Icons]
#ifdef HaveAppIcon
Name: "{autoprograms}\{#MyAppName}"; Filename: "{sys}\wscript.exe"; Parameters: "//nologo ""{app}\PassionExcel.vbs"""; WorkingDir: "{app}"; Comment: "Lancer la consultation documentaire"; IconFilename: "{app}\app_icon.ico"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{sys}\wscript.exe"; Parameters: "//nologo ""{app}\PassionExcel.vbs"""; WorkingDir: "{app}"; Tasks: desktopicon; IconFilename: "{app}\app_icon.ico"
#else
Name: "{autoprograms}\{#MyAppName}"; Filename: "{sys}\wscript.exe"; Parameters: "//nologo ""{app}\PassionExcel.vbs"""; WorkingDir: "{app}"; Comment: "Lancer la consultation documentaire"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{sys}\wscript.exe"; Parameters: "//nologo ""{app}\PassionExcel.vbs"""; WorkingDir: "{app}"; Tasks: desktopicon
#endif

[Run]
Filename: "{sys}\wscript.exe"; Parameters: "//nologo ""{app}\PassionExcel.vbs"""; WorkingDir: "{app}"; Description: "Lancer {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\.venv"
Type: filesandordirs; Name: "{app}\python"

[Code]
function DirEmbedPython: Boolean;
begin
  Result := DirExists(ExpandConstant('{src}\embed\python'));
end;
