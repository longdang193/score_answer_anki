$ErrorActionPreference = 'Stop'

$src = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$dst = 'C:\Users\HOANG PHI LONG DANG\AppData\Roaming\Anki2\addons21\score_answer'

$runtimeFiles = @(
    '__init__.py',
    'locales.py',
    'config_model.py',
    'ai_runtime.py',
    'reviewer_ui.py',
    'config.json',
    'manifest.json',
    'README.md',
    'Config.md'
) | ForEach-Object { Join-Path $src $_ }

Copy-Item $runtimeFiles -Destination $dst -Force
Remove-Item (Join-Path $dst 'prompt_defaults.json') -Force -ErrorAction SilentlyContinue
robocopy (Join-Path $src 'configs') (Join-Path $dst 'configs') /MIR | Out-Null
robocopy (Join-Path $src 'images') (Join-Path $dst 'images') /MIR | Out-Null

Write-Host "Synced to $dst"
