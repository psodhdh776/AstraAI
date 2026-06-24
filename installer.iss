; Astra AI Inno Setup installer
[Setup]
AppName=Astra AI
AppVersion=1.4.0
AppPublisher=Anomalyco
DefaultDirName={autopf}\Astra AI
DefaultGroupName=Astra AI
UninstallDisplayIcon={app}\AstraAI.exe
OutputDir=dist
OutputBaseFilename=AstraAI_Setup
SetupIconFile=data\icon.ico
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin

[Files]
Source: "dist\AstraAI.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "modules\*"; DestDir: "{app}\modules"; Flags: ignoreversion recursesubdirs
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs
Source: "data\*"; DestDir: "{app}\data"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\Astra AI"; Filename: "{app}\AstraAI.exe"
Name: "{group}\Uninstall Astra AI"; Filename: "{uninstallexe}"
Name: "{commondesktop}\Astra AI"; Filename: "{app}\AstraAI.exe"

[Run]
Filename: "{app}\AstraAI.exe"; Description: "Запустить Astra AI"; Flags: postinstall nowait skipifsilent

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "AstraAI"; ValueData: "{app}\AstraAI.exe"; Flags: uninsdeletevalue
