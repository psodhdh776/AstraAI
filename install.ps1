$projectDir = "C:\Users\admin\Desktop\AbsoluteAssistant"
$appName = "Astra AI"

Write-Host "Installing $appName..." -ForegroundColor Cyan

# 1. Create launcher batch
$launcher = '@echo off
title Astra AI
echo Starting Astra AI...
cd /d "%~dp0"
start "" "python" app.py
exit'
Set-Content -Path "$projectDir\AstraAI.bat" -Value $launcher
Write-Host "[OK] Launcher created" -ForegroundColor Green

# 2. Desktop shortcut
$ws = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath("Desktop")
$sc = $ws.CreateShortcut("$desktop\$appName.lnk")
$sc.TargetPath = "$projectDir\AstraAI.bat"
$sc.WorkingDirectory = $projectDir
$sc.Description = "Astra AI - offline voice assistant"
$sc.Save()
Write-Host "[OK] Desktop shortcut created" -ForegroundColor Green

# 3. Start Menu shortcut
$startMenu = [Environment]::GetFolderPath("Programs")
$sm = $ws.CreateShortcut("$startMenu\$appName.lnk")
$sm.TargetPath = "$projectDir\AstraAI.bat"
$sm.WorkingDirectory = $projectDir
$sm.Description = "Astra AI - offline voice assistant"
$sm.Save()
Write-Host "[OK] Start Menu shortcut created" -ForegroundColor Green

# 4. Uninstaller
$uninstall = '@echo off
title Uninstall Astra AI
echo Removing Astra AI shortcuts...
set SHORTCUT=%USERPROFILE%\Desktop\' + $appName + '.lnk
set SMSHORTCUT=%APPDATA%\Microsoft\Windows\Start Menu\Programs\' + $appName + '.lnk
if exist "%SHORTCUT%" del "%SHORTCUT%"
if exist "%SMSHORTCUT%" del "%SMSHORTCUT%"
echo Shortcuts removed. To fully remove, delete the folder:
echo ' + $projectDir + '
pause'
Set-Content -Path "$projectDir\Uninstall_AstraAI.bat" -Value $uninstall
Write-Host "[OK] Uninstaller created" -ForegroundColor Green

Write-Host ""
Write-Host "=== Installation complete ===" -ForegroundColor Cyan
Write-Host "Desktop: $desktop\$appName.lnk" -ForegroundColor Yellow
Write-Host "Start Menu: $appName" -ForegroundColor Yellow
Write-Host "Uninstall: $projectDir\Uninstall_AstraAI.bat" -ForegroundColor Yellow
