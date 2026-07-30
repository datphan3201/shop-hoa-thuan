#define AppName "Shop Hoà Thuận"
#define AppVersion "0.1.0"
#define AppPublisher "Shop Hoà Thuận"
#define AppExeName "ShopHoaThuanServer.exe"

[Setup]
AppId={{A8309A93-F880-4D73-A076-0A480783AF7F}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\Shop Hoa Thuan
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\..\dist\installer
OutputBaseFilename=ShopHoaThuan-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExeName}

[Files]
Source: "..\..\dist\ShopHoaThuan\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\winsw\ShopHoaThuanService.xml"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\vendor\WinSW-x64.exe"; DestDir: "{app}"; DestName: "ShopHoaThuanService.exe"; Flags: ignoreversion

[Icons]
Name: "{autodesktop}\Shop Hoà Thuận"; Filename: "http://127.0.0.1:8765/"
Name: "{group}\Shop Hoà Thuận"; Filename: "http://127.0.0.1:8765/"

[Run]
Filename: "{app}\ShopHoaThuanService.exe"; Parameters: "install"; Flags: runhidden waituntilterminated
Filename: "{app}\ShopHoaThuanService.exe"; Parameters: "start"; Flags: runhidden waituntilterminated
Filename: "http://127.0.0.1:8765/setup/"; Description: "Mở Shop Hoà Thuận"; Flags: shellexec postinstall skipifsilent nowait

[UninstallRun]
Filename: "{app}\ShopHoaThuanService.exe"; Parameters: "stop"; Flags: runhidden waituntilterminated skipifdoesntexist
Filename: "{app}\ShopHoaThuanService.exe"; Parameters: "uninstall"; Flags: runhidden waituntilterminated skipifdoesntexist

[Dirs]
Name: "{commonappdata}\Shop Hoa Thuan"; Permissions: users-modify
