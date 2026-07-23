; PPC — Programming Cycling Coach installer (NSIS)
; Installazione in Program Files; i dati utente restano in %USERPROFILE%\.domestique\
; e NON vengono toccati da installazione/aggiornamento (così connessioni e piani
; sopravvivono senza migrazione).

!define APPNAME "PPC"
!define APPNAMEFULL "PPC - Programming Cycling Coach"
!define PUBLISHER "PPC"
!define VERSION "3.5.2"
!define INSTDIR "$PROGRAMFILES64\PPC"

Name "${APPNAMEFULL}"
OutFile "PPC-Setup-${VERSION}.exe"
InstallDir "${INSTDIR}"
RequestExecutionLevel admin

; I dati utente vivono fuori da INSTDIR -> non li includiamo e non li cancelliamo.
InstallDirRegKey HKLM "Software\PPC" "InstallDir"

Section "Install"
  SetOutPath "$INSTDIR"
  ; I file dell'app (EXE + dipendenze bundle da PyInstaller) vanno qui.
  File /r "dist\PPC\*.*"

  ; Scorciatoia nel menu Start
  CreateDirectory "$SMPROGRAMS\${APPNAME}"
  CreateShortCut "$SMPROGRAMS\${APPNAME}\${APPNAMEFULL}.lnk" "$INSTDIR\PPC.exe" "" "$INSTDIR\PPC.exe" 0
  CreateShortCut "$DESKTOP\${APPNAMEFULL}.lnk" "$INSTDIR\PPC.exe" "" "$INSTDIR\PPC.exe" 0

  ; Disinstallatore
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PPC" "DisplayName" "${APPNAMEFULL}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PPC" "UninstallString" "$INSTDIR\Uninstall.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PPC" "DisplayVersion" "${VERSION}"
  WriteRegStr HKLM "Software\PPC" "InstallDir" "$INSTDIR"
SectionEnd

Section "Uninstall"
  ; NOTA: NON cancelliamo %USERPROFILE%\.domestique\ (dati/connessioni utente).
  Delete "$SMPROGRAMS\${APPNAME}\${APPNAMEFULL}.lnk"
  Delete "$DESKTOP\${APPNAMEFULL}.lnk"
  RMDir "$SMPROGRAMS\${APPNAME}"
  RMDir /r "$INSTDIR"
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PPC"
  DeleteRegKey HKLM "Software\PPC"
SectionEnd
