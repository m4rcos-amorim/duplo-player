; Duplo Player installer (Inno Setup 6).
; Build it with:  .\installer.ps1   (needs dist\DuploPlayer created by build.ps1)

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
AppId={{8F3B6C1E-52D4-4A7B-9C0E-3D5A1B7E94F2}
AppName=Duplo Player
AppVersion={#AppVersion}
AppPublisher=Marcos Vinicius de Almeida Amorim
DefaultDirName={autopf}\Duplo Player
DefaultGroupName=Duplo Player
DisableProgramGroupPage=yes
; Installs for the current user only (no administrator prompt). The user may choose "all users".
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
SetupIconFile=..\assets\duplo.ico
UninstallDisplayIcon={app}\DuploPlayer.exe
OutputDir=..\dist-installer
OutputBaseFilename=DuploPlayer-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Ask for the language only when the Windows language is not one of the two above.
ShowLanguageDialog=auto

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\DuploPlayer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Duplo Player"; Filename: "{app}\DuploPlayer.exe"
Name: "{autodesktop}\Duplo Player"; Filename: "{app}\DuploPlayer.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\DuploPlayer.exe"; Description: "{cm:LaunchProgram,Duplo Player}"; Flags: nowait postinstall skipifsilent
