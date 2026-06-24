@echo off
title Uninstall Astra AI
echo Removing Astra AI shortcuts...
set SHORTCUT=%USERPROFILE%\Desktop\Astra AI.lnk
set SMSHORTCUT=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Astra AI.lnk
if exist "%SHORTCUT%" del "%SHORTCUT%"
if exist "%SMSHORTCUT%" del "%SMSHORTCUT%"
echo Shortcuts removed. To fully remove, delete the folder:
echo C:\Users\admin\Desktop\AbsoluteAssistant
pause
