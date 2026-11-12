; Social Empires Türkçe: Windows kurulum programı (Inno Setup 6).
;
; araclar/exe_paketi.py --klasor ile üretilen klasörü kullanıcının kendi program klasörüne kurar
; (%LOCALAPPDATA%\Programs\SocialEmpiresTR; yönetici izni istemez), masaüstüne ve Başlat menüsüne kısayol
; koyar, Programlar ve Özellikler'e kaldırıcı ekler. Kayıtlar, ayarlar, modlar ve indirilen oyun dosyaları
; programın yanında oluşur (oyun/yollar.py BASE_DIR); kaldırıcı yalnızca kurduğu dosyaları siler, bunlar kalır.
; Yeni sürüm aynı klasöre kurulur, kayıtlar korunur.
;
; Derleme (CI: .github/workflows/windows.yml kurulum işi):
;   iscc /DSurum=0.1.0 /DKaynak=..\dist\SocialEmpiresTR /DCikti=..\dist /DSimge=..\dist\simge.ico
;        /DAd=SocialEmpiresTR-0.1.0-windows-kurulum araclar\kurulum.iss

#ifndef Surum
  #define Surum "0.0.0"
#endif
#ifndef Kaynak
  #define Kaynak "..\dist\SocialEmpiresTR"
#endif
#ifndef Cikti
  #define Cikti "..\dist"
#endif
#ifndef Ad
  #define Ad "SocialEmpiresTR-kurulum"
#endif
#ifndef Simge
  ; exe_paketi.simge_ico(templates/img/simge-192.png) ile derlemede üretilir
  #define Simge "..\dist\simge.ico"
#endif

[Setup]
; Kimlik sabittir: yeni sürüm eskisinin üzerine kurulur, kaldırıcı tek kalır
AppId={{6E0C5A2B-2F4E-4C1B-9B57-5E3D2B8A41C7}
AppName=Social Empires Türkçe
AppVersion={#Surum}
AppPublisher=Social Empires Türkçe
AppPublisherURL=https://github.com/lahmacunveayran/socialempires-tr
AppSupportURL=https://github.com/lahmacunveayran/socialempires-tr/issues
DefaultDirName={localappdata}\Programs\SocialEmpiresTR
DefaultGroupName=Social Empires Türkçe
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir={#Cikti}
OutputBaseFilename={#Ad}
SetupIconFile={#Simge}
UninstallDisplayIcon={app}\SocialEmpiresTR.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=..\LICENSE
; Oyun açıkken (sunucu çalışırken) kurulum/kaldırma dosyaları kilitli bulmasın
CloseApplications=yes

[Languages]
Name: "tr"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "masaustu"; Description: "Masaüstüne kısayol koy"; GroupDescription: "Kısayollar:"

[Files]
Source: "{#Kaynak}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
; Kayıt klasörü kurulumda açılır ve kaldırmada hiç silinmez
Name: "{app}\saves"; Flags: uninsneveruninstall

[Icons]
Name: "{group}\Social Empires Türkçe"; Filename: "{app}\SocialEmpiresTR.exe"; WorkingDir: "{app}"
Name: "{group}\Kayıtlar klasörü"; Filename: "{app}\saves"
Name: "{group}\Social Empires Türkçe'yi kaldır"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Social Empires Türkçe"; Filename: "{app}\SocialEmpiresTR.exe"; WorkingDir: "{app}"; Tasks: masaustu

[Run]
Filename: "{app}\SocialEmpiresTR.exe"; WorkingDir: "{app}"; Description: "Oyunu şimdi aç"; Flags: nowait postinstall skipifsilent
