; ============================================================
;  M-NEO VMS — Minimal Working Installer (No Icons, No Images)
; ============================================================

#define AppName "M-Neo VMS"
#define AppVersion "1.0.0"
#define DistDir "dist\\M-Neo VMS"

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={pf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
AllowNoIcons=yes

; No icons, no wizard images
WizardStyle=modern

Compression=lzma
SolidCompression=yes
OutputDir="installer_output"
OutputBaseFilename="MNeoVMS_Setup"

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

[Icons]
; Start menu shortcut (no icon specified → uses default exe icon)
Name:"{group}\M-Neo VMS"; Filename:"{app}\M-Neo VMS.exe"

; Desktop shortcut
Name:"{commondesktop}\M-Neo VMS"; Filename:"{app}\M-Neo VMS.exe"; Tasks:desktopicon

[Tasks]
Name:"desktopicon"; Description:"Create desktop shortcut"; Flags:checkedonce

[Run]
Filename:"{app}\M-Neo VMS.exe"; Description:"Launch M-Neo VMS"; Flags:nowait postinstall skipifsilent
