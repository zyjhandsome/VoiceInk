; VoiceInk Installation Script for Inno Setup 6
; Creates a professional Windows installer with custom installation path
;
; Version constants are normally passed by build_installer.py:
;   ISCC /DAppVersionStr=1.3.0 /DAppVersionQuad=1.3.0.0 VoiceInk-Setup.iss
#ifndef AppVersionStr
#define AppVersionStr "1.3.0"
#endif
#ifndef AppVersionQuad
#define AppVersionQuad "1.3.0.0"
#endif

[Setup]
AppName=VoiceInk
AppVersion={#AppVersionStr}
AppPublisher=VoiceInk
AppPublisherURL=https://github.com/zyjhandsome/VoiceInk
AppSupportURL=https://github.com/zyjhandsome/VoiceInk/issues
DefaultDirName={commonpf}\VoiceInk
DefaultGroupName=VoiceInk
AllowNoIcons=yes
OutputDir=..\dist
OutputBaseFilename=VoiceInk-Setup-{#AppVersionStr}
SetupIconFile=..\voiceink\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
UninstallDisplayIcon={app}\VoiceInk.exe
UninstallDisplayName=VoiceInk
DirExistsWarning=no
; 确保显示安装路径选择界面
DisableDirPage=no

; Version info
VersionInfoVersion={#AppVersionQuad}
VersionInfoCompany=VoiceInk
VersionInfoDescription=VoiceInk Setup
VersionInfoCopyright=VoiceInk
VersionInfoProductName=VoiceInk
VersionInfoProductVersion={#AppVersionQuad}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "开机自动启动"; GroupDescription: "启动选项"; Flags: unchecked

[Files]
; Paths match build.py PyInstaller output: dist\VoiceInk\
Source: "..\dist\VoiceInk\VoiceInk.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\VoiceInk\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
; Models copied by build.py when present (optional at compile time)
Source: "..\dist\VoiceInk\models\*"; DestDir: "{app}\models"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

[Icons]
Name: "{group}\VoiceInk"; Filename: "{app}\VoiceInk.exe"
Name: "{group}\访问官网"; Filename: "https://github.com/zyjhandsome/VoiceInk"
Name: "{group}\卸载 VoiceInk"; Filename: "{uninstallexe}"
Name: "{autodesktop}\VoiceInk"; Filename: "{app}\VoiceInk.exe"; Tasks: desktopicon

[Registry]
; Auto-start on Windows boot (optional)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "VoiceInk"; ValueData: """{app}\VoiceInk.exe"""; Tasks: autostart; Flags: uninsdeletevalue
; App paths for Windows to find the executable
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\VoiceInk.exe"; ValueType: string; ValueName: ""; ValueData: "{app}\VoiceInk.exe"; Flags: uninsdeletekey

[Run]
Filename: "{app}\VoiceInk.exe"; Description: "立即运行 VoiceInk"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "taskkill"; Parameters: "/F /IM VoiceInk.exe"; Flags: runhidden waituntilterminated

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
function InitializeSetup(): Boolean;
var
  ErrorCode: Integer;
begin
  // Kill any running VoiceInk process before installing
  Exec('taskkill', '/F /IM VoiceInk.exe', '', SW_HIDE, ewWaitUntilTerminated, ErrorCode);
  Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  VoiceInkDataDir: string;
begin
  if CurUninstallStep = usUninstall then
  begin
    // Ask user if they want to delete user data
    VoiceInkDataDir := ExpandConstant('{%USERPROFILE}\.voiceink');
    if DirExists(VoiceInkDataDir) then
    begin
      if MsgBox('是否删除用户配置和模型数据？', mbConfirmation, MB_YESNO) = IDYES then
        DelTree(VoiceInkDataDir, True, True, True);
    end;
  end;
end;