; VoiceInk Installation Script for Inno Setup 6
; Creates a professional Windows installer with custom installation path

[Setup]
AppName=VoiceInk
AppVersion=1.2.0
AppPublisher=VoiceInk
AppPublisherURL=https://github.com/zyjhandsome/VoiceInk
AppSupportURL=https://github.com/zyjhandsome/VoiceInk/issues
DefaultDirName={commonpf}\VoiceInk
DefaultGroupName=VoiceInk
AllowNoIcons=yes
OutputDir=..\dist
OutputBaseFilename=VoiceInk-Setup
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
VersionInfoVersion=1.2.0.0
VersionInfoCompany=VoiceInk
VersionInfoDescription=VoiceInk Setup
VersionInfoCopyright=VoiceInk
VersionInfoProductName=VoiceInk
VersionInfoProductVersion=1.2.0.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "开机自动启动"; GroupDescription: "启动选项"; Flags: unchecked

[Files]
; Main executable
Source: "..\dist\VoiceInk_final\VoiceInk\VoiceInk.exe"; DestDir: "{app}"; Flags: ignoreversion
; Internal dependencies
Source: "..\dist\VoiceInk_final\VoiceInk\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
; Qwen3-ASR model (bundled)
Source: "..\dist\VoiceInk_final\VoiceInk\models\*"; DestDir: "{app}\models"; Flags: ignoreversion recursesubdirs createallsubdirs

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