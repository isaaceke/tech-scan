@echo off
if exist "%~dp0Enugu Air Online Access Panel.exe" (
    start "" "%~dp0Enugu Air Online Access Panel.exe"
) else (
    start "" /b "C:\Python314\pythonw.exe" "%~dp0control_center\online_control_center.py"
)
