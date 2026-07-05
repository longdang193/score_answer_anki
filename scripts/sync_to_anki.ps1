$ErrorActionPreference = 'Stop'

$src = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$dst = 'C:\Users\HOANG PHI LONG DANG\AppData\Roaming\Anki2\addons21\score_answer'

Copy-Item "$src\__init__.py","$src\config.json","$src\manifest.json","$src\README.md","$src\Config.md" -Destination $dst -Force
robocopy "$src\images" "$dst\images" /MIR | Out-Null

Write-Host "Synced to $dst"
