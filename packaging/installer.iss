; Inno Setup script - cria o instalador profissional do MediaAutomationServer.
;
; Como usar:
;   1. Instale o Inno Setup 6: https://jrsoftware.org/isdl.php
;   2. Gere o exe com PyInstaller primeiro (ver MediaAutomationServer.spec).
;   3. Abra este arquivo no Inno Setup Compiler e clique em "Compile".
;
; Saida: packaging/output/MediaAutomationServer-Setup-X.Y.Z.exe

#define AppName "MediaAutomationServer"
#define AppVersion "0.7.12"
#define AppPublisher "Sua Igreja"
#define AppExeName "MediaAutomationServer.exe"

[Setup]
AppId={{A2F8C3D4-1234-5678-9ABC-DEF012345678}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename={#AppName}-Setup-{#AppVersion}
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern
; Requer admin (UAC) pra instalar em C:\Program Files [(x86)].
; {autopf} resolve automaticamente: 64-bit -> "Program Files",
; 32-bit -> "Program Files (x86)".
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
; MinVersion: omitido. Inno Setup 6 ja requer Win 7+ por padrao;
; verificacao de "Win 10 ou superior" pode ser adicionada via [Code]
; se necessario no futuro.
UninstallDisplayIcon={app}\{#AppExeName}

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na area de trabalho"; GroupDescription: "Atalhos:"
Name: "startupshortcut"; Description: "Iniciar com o Windows"; GroupDescription: "Atalhos:"; Flags: unchecked

[Files]
Source: "..\dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon
Name: "{userstartup}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: startupshortcut

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Abrir {#AppName}"; Flags: nowait postinstall skipifsilent
