; DeepSeek Harness Desktop Installer
; Creates a proper Windows application with Start Menu and Desktop shortcuts

Name "DeepSeek Harness"
OutFile "DeepSeek-Harness-Setup.exe"
InstallDir "$PROGRAMFILES64\DeepSeek Harness"
RequestExecutionLevel admin

!include "MUI2.nsh"

; Modern UI pages
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "SimpChinese"

; Install files
Section "Install"
  SetOutPath "$INSTDIR"
  
  ; Main executable (Python launcher wrapped)
  File "deepseek-harness-desktop.exe"
  
  ; Share resources
  SetOutPath "$INSTDIR\share\icons\hicolor\256x256\apps"
  File "..\..\share\icons\hicolor\256x256\apps\deepseek-harness-desktop.png"
  
  SetOutPath "$INSTDIR\share\icons\hicolor\scalable\apps"
  File "..\..\share\icons\hicolor\scalable\apps\deepseek-harness-desktop.svg"
  
  SetOutPath "$INSTDIR\share\icons\windows"
  File "..\..\share\icons\windows\deepseek-harness-desktop.ico"
  
  ; Create shortcuts
  CreateShortcut "$DESKTOP\DeepSeek Harness.lnk" "$INSTDIR\deepseek-harness-desktop.exe"
  CreateShortcut "$STARTMENU\DeepSeek Harness\DeepSeek Harness.lnk" "$INSTDIR\deepseek-harness-desktop.exe"
  CreateShortcut "$STARTMENU\DeepSeek Harness\Uninstall.lnk" "$INSTDIR\uninst.exe"
  
  ; Write uninstaller
  WriteUninstaller "$INSTDIR\uninst.exe"
  
  ; Register in Add/Remove Programs
  WriteRegStr HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\DeepSeekHarness" \
    "DisplayName" "DeepSeek Harness"
  WriteRegStr HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\DeepSeekHarness" \
    "UninstallString" "$INSTDIR\uninst.exe"
  WriteRegStr HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\DeepSeekHarness" \
    "DisplayIcon" "$INSTDIR\deepseek-harness-desktop.exe"
SectionEnd

; Uninstaller
Section "Uninstall"
  Delete "$DESKTOP\DeepSeek Harness.lnk"
  RMDir /r "$STARTMENU\DeepSeek Harness"
  Delete "$INSTDIR\*"
  RMDir /r "$INSTDIR"
  DeleteRegKey HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\DeepSeekHarness"
SectionEnd
