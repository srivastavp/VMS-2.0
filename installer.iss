; ============================================================
;  M-NEO VMS — Update-Safe Installer
; ============================================================

#define AppName "M-Neo VMS"
#define AppVersion "1.1.0"
#define DistDir "dist\\M-Neo VMS"

[Setup]
AppId={{B7A1F5D4-6E2A-4B0C-9F1E-MNEOVMS}}
AppName={#AppName}
AppVersion={#AppVersion}

DefaultDirName={pf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
AllowNoIcons=yes

WizardStyle=modern

Compression=lzma
SolidCompression=yes
OutputDir="installer_output"
OutputBaseFilename="MNeoVMS_Setup_{#AppVersion}"

PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64

UninstallDisplayName={#AppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; Main EXE
Source:"{#DistDir}\M-Neo VMS.exe"; DestDir:"{app}"; Flags:ignoreversion

; Full app folder (recursive)
Source:"{#DistDir}\*"; DestDir:"{app}"; Flags:ignoreversion recursesubdirs createallsubdirs

[Tasks]
Name:"desktopicon"; Description:"Create desktop shortcut"; Flags:checkedonce

[Icons]
Name:"{group}\M-Neo VMS"; Filename:"{app}\M-Neo VMS.exe"
Name:"{commondesktop}\M-Neo VMS"; Filename:"{app}\M-Neo VMS.exe"; Tasks:desktopicon

[Run]
Filename:"{app}\M-Neo VMS.exe"; Description:"Launch M-Neo VMS"; Flags:nowait postinstall skipifsilent
