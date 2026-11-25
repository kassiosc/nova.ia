#define MyAppName "NOVA AI"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "NOVA AI"

#define ProjectRoot AddBackslash(SourcePath) + ".."

[Setup]
AppId={{A82F5B31-6C92-4B9D-9A72-1D8C7E4F2036}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\NOVA-AI
DefaultGroupName=NOVA AI
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=Output
OutputBaseFilename=NOVA-AI-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile={#ProjectRoot}\instalador\identidade\NOVA-AI.ico
WizardImageFile={#ProjectRoot}\instalador\identidade\NOVA-AI-Wizard.bmp
WizardSmallImageFile={#ProjectRoot}\instalador\identidade\NOVA-AI-WizardSmall.bmp
UninstallDisplayIcon={app}\NOVA-AI.exe
SetupLogging=yes

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; Flags: unchecked

[Files]
Source: "{#ProjectRoot}\instalador\build\NOVA-AI\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#ProjectRoot}\instalador\payload\OllamaSetup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "{#ProjectRoot}\instalador\payload\ollama\models\*"; DestDir: "{code:GetUserProfile}\.ollama\models"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#ProjectRoot}\instalador\payload\ollama\models\blobs\sha256-b5c0e5cf74cf51af1ecbc4af597cfcd13fd9925611838884a681070838a14a50"; DestDir: "{app}\licenses"; DestName: "QWEN-RESEARCH-LICENSE.txt"; Flags: ignoreversion

[Icons]
Name: "{group}\NOVA AI"; Filename: "{app}\NOVA-AI.exe"
Name: "{autodesktop}\NOVA AI"; Filename: "{app}\NOVA-AI.exe"; Tasks: desktopicon

[Run]
Filename: "{tmp}\OllamaSetup.exe"; Parameters: "/VERYSILENT /NORESTART /SUPPRESSMSGBOXES"; StatusMsg: "Instalando Ollama..."; Flags: waituntilterminated runhidden; Check: not IsOllamaInstalled
Filename: "{app}\NOVA-AI.exe"; Description: "Abrir NOVA AI"; Flags: postinstall nowait skipifsilent

[Code]
function GetUserProfile(Param: String): String;
begin
  Result := GetEnv('USERPROFILE');
end;
function IsOllamaInstalled: Boolean;
begin
  Result :=
    FileExists(ExpandConstant('{localappdata}\Programs\Ollama\ollama.exe')) or
    FileExists(ExpandConstant('{autopf}\Ollama\ollama.exe')) or
    FileExists(ExpandConstant('{autopf32}\Ollama\ollama.exe'));
end;
