#ifndef Version
  #error Version must be supplied by the build script.
#endif
#ifndef Bundle
  #error Bundle must be supplied by the build script.
#endif
#ifndef ProductIcon
  #error ProductIcon must be supplied by the build script.
#endif

[Setup]
AppId={{C3C5D25E-293A-4F0E-BB10-750017A14384}
AppName=RadixScope
AppVersion={#Version}
AppPublisher=Koreapanda4444
AppPublisherURL=https://github.com/Koreapanda4444/radixscope
DefaultDirName={localappdata}\Programs\RadixScope
DefaultGroupName=RadixScope
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
UninstallDisplayIcon={app}\RadixScope.exe
OutputBaseFilename=RadixScope-{#Version}-windows-x64-setup
SetupIconFile={#ProductIcon}
VersionInfoVersion={#Version}
VersionInfoProductVersion={#Version}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ChangesAssociations=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; Flags: unchecked

[Files]
Source: "{#Bundle}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\RadixScope"; Filename: "{app}\RadixScope.exe"
Name: "{autodesktop}\RadixScope"; Filename: "{app}\RadixScope.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\RadixScope.exe"; Description: "{cm:LaunchProgram,RadixScope}"; Flags: nowait postinstall skipifsilent
