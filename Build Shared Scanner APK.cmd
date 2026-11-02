@echo off
setlocal
"C:\Python314\python.exe" "%~dp0control_center\build_apk.py"
if errorlevel 1 (
  echo Build not completed. Follow the message above; the existing APK was not replaced.
  pause
  exit /b 1
)
echo APK updated for the scanner folder selected in the access panel.
pause
