#define AppName "Shop Hoà Thuận"
#ifndef AppVersion
  #error AppVersion must be supplied from pyproject.toml by the Windows build script.
#endif
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
Source: "..\..\dist\ShopHoaThuanMigration\*"; DestDir: "{app}\ShopHoaThuanMigration"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\dist\ShopHoaThuanHealth.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\dist\ShopHoaThuanLauncher.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\dist\ShopHoaThuanUpdate.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\dist\ShopHoaThuanBackup.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\dist\ShopHoaThuanRestore.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\winsw\ShopHoaThuanService.xml"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\vendor\WinSW-x64.exe"; DestDir: "{app}"; DestName: "ShopHoaThuanService.exe"; Flags: ignoreversion
Source: "configure_firewall.ps1"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autodesktop}\Shop Hoà Thuận"; Filename: "{app}\ShopHoaThuanLauncher.exe"
Name: "{group}\Shop Hoà Thuận"; Filename: "{app}\ShopHoaThuanLauncher.exe"
Name: "{group}\Sao lưu Shop Hoà Thuận"; Filename: "{app}\ShopHoaThuanBackup.exe"
Name: "{group}\Khôi phục Shop Hoà Thuận"; Filename: "{app}\ShopHoaThuanRestore.exe"
Name: "{group}\Cập nhật Shop Hoà Thuận"; Filename: "{app}\ShopHoaThuanUpdate.exe"

[Run]
Filename: "{app}\ShopHoaThuanMigration\ShopHoaThuanMigration.exe"; Parameters: ""; Flags: runhidden waituntilterminated
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File ""{app}\configure_firewall.ps1"" -Action Install -ProgramPath ""{app}\ShopHoaThuanServer.exe"""; StatusMsg: "Đang cấu hình firewall LAN cho profile Private/Public..."; Flags: runhidden waituntilterminated
Filename: "{app}\ShopHoaThuanService.exe"; Parameters: "install"; Flags: runhidden waituntilterminated
Filename: "{app}\ShopHoaThuanService.exe"; Parameters: "start"; Flags: runhidden waituntilterminated
Filename: "http://127.0.0.1:2505/"; Description: "Mở Shop Hoà Thuận"; Flags: shellexec postinstall skipifsilent nowait

[UninstallRun]
Filename: "{app}\ShopHoaThuanService.exe"; Parameters: "stop"; Flags: runhidden waituntilterminated skipifdoesntexist; RunOnceId: "ShopHoaThuanServiceStop"
Filename: "{app}\ShopHoaThuanService.exe"; Parameters: "uninstall"; Flags: runhidden waituntilterminated skipifdoesntexist; RunOnceId: "ShopHoaThuanServiceUninstall"
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File ""{app}\configure_firewall.ps1"" -Action Remove -ProgramPath ""{app}\ShopHoaThuanServer.exe"""; Flags: runhidden waituntilterminated skipifdoesntexist; RunOnceId: "ShopHoaThuanFirewallRemove"

[Dirs]
Name: "{commonappdata}\Shop Hoa Thuan"; Permissions: users-modify
Name: "{commonappdata}\Shop Hoa Thuan\data"; Permissions: users-modify
Name: "{commonappdata}\Shop Hoa Thuan\data\media"; Permissions: users-modify
Name: "{commonappdata}\Shop Hoa Thuan\backups"; Permissions: users-modify
Name: "{commonappdata}\Shop Hoa Thuan\rollback"; Permissions: users-modify
Name: "{commonappdata}\Shop Hoa Thuan\logs"; Permissions: users-modify
Name: "{commonappdata}\Shop Hoa Thuan\config"; Permissions: users-modify
