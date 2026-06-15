$WScriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptShell.CreateShortcut("$env:USERPROFILE\Desktop\AI提示词生成器.lnk")
$Shortcut.TargetPath = "$PSScriptRoot\启动.bat"
$Shortcut.WorkingDirectory = "$PSScriptRoot"
$Shortcut.Save()
Write-Host "Desktop shortcut created successfully."
