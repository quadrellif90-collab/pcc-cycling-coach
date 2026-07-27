; PCC — Performance Cycling Coach installer (NSIS)
; Installazione in Program Files; i dati utente restano in %USERPROFILE%\.domestique\
; e NON vengono toccati da installazione/aggiornamento (così connessioni e piani
; sopravvivono senza migrazione).

; Build Unicode: gestisce correttamente i caratteri non-ASCII (es. em-dash "—" nel
; nome completo) invece di mostrarli come mojibake (â€") nel nome app/collegamenti.
Unicode true

!define APPNAME "PCC Pro"
!define APPNAMEFULL "PCC Pro — Adaptive Cycling Intelligence"
!define PUBLISHER "PCC Pro"
; VERSION è passata dal CI come /DVERSION=X.Y.Z
; Default di sicurezza se compilato a mano senza /D.
!ifndef VERSION
  !define VERSION "4.0.0"
!endif
!define INSTDIR "$PROGRAMFILES64\PCC"

Name "${APPNAMEFULL}"
; OutFile assoluto per evitare ambiguità di cwd su CI (GitHub Actions).
; Define OUTDIR passato dal CI; default alla cartella corrente se compilato a mano.
!ifndef OUTDIR
  !define OUTDIR "."
!endif
OutFile "${OUTDIR}\PCC-Setup-${VERSION}.exe"
InstallDir "${INSTDIR}"
RequestExecutionLevel admin

; I dati utente vivono fuori da INSTDIR -> non li includiamo e non li cancelliamo.
InstallDirRegKey HKLM "Software\PCC" "InstallDir"

Section "Install"
  SetOutPath "$INSTDIR"
  ; I file dell'app (EXE + dipendenze bundle da PyInstaller) vanno qui.
  File /r "dist\PCC\*.*"

  ; Scorciatoia nel menu Start
  CreateDirectory "$SMPROGRAMS\${APPNAME}"
  CreateShortCut "$SMPROGRAMS\${APPNAME}\${APPNAMEFULL}.lnk" "$INSTDIR\PCC.exe" "" "$INSTDIR\PCC.exe" 0
  CreateShortCut "$DESKTOP\${APPNAMEFULL}.lnk" "$INSTDIR\PCC.exe" "" "$INSTDIR\PCC.exe" 0

  ; Disinstallatore
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PCC" "DisplayName" "${APPNAMEFULL}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PCC" "UninstallString" "$INSTDIR\Uninstall.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PCC" "DisplayVersion" "${VERSION}"
  WriteRegStr HKLM "Software\PCC" "InstallDir" "$INSTDIR"
SectionEnd

Section "Uninstall"
  ; NOTA: NON cancelliamo %USERPROFILE%\.domestique\ (dati/connessioni utente).
  Delete "$SMPROGRAMS\${APPNAME}\${APPNAMEFULL}.lnk"
  Delete "$DESKTOP\${APPNAMEFULL}.lnk"
  RMDir "$SMPROGRAMS\${APPNAME}"
  RMDir /r "$INSTDIR"
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PCC"
  DeleteRegKey HKLM "Software\PCC"
SectionEnd
