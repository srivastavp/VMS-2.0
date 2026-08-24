; Inno Setup installer script for M-Neo VMS
; Requires Inno Setup (free) from https://jrsoftware.org/isinfo.php
; Build steps:
;   1. Build EXE with PyInstaller (onedir): see README or build notes
;   2. Install Inno Setup
;   3. Open this file in Inno Setup Compiler and click Build
;   4. The installer will be created in the OutputDir below

#define MyAppName "M-Neo VMS"
#define MyAppVersion "1.0"
#define MyAppPublisher "M-Neo Solutions"
#define MyAppExeName "M-Neo VMS.exe"
#define MyAppAssocName MyAppName + " File"
#define MyAppAssocExt ""
#define MyAppAssocKey StringChange(MyAppAssocName, " ", "") + MyAppAssocExt

[Setup]
AppId={{MNEO_VMS_2025}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
OutputDir=C:\Users\Pranav Srivastav\Desktop\ATTMS\VMS-2.0\dist\installer
OutputBaseFilename=M-Neo-VMS-Setup-{#MyAppVersion}
SetupIconFile=C:\Users\Pranav Srivastav\Desktop\ATTMS\VMS-2.0\assets\logo.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Copy the entire onedir build produced by PyInstaller
; Build with: pyinstaller --name "M-Neo VMS" --windowed --icon=assets/logo.ico --add-data "assets;assets" --add-data "data;data" main.py
Source: "C:\Users\Pranav Srivastav\Desktop\ATTMS\VMS-2.0\dist\M-Neo VMS\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Optional: remove app data on uninstall (user can keep it if desired)
; Type: filesandordirs; Name: "{app}"
