# Explicit owner action; no admin, global package install, OAuth or upload.
param([ValidateSet('Setup','Pilot','Review','Acceptance')][string]$Mode='Setup', [string]$Wheelhouse='')
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$homeDir=Join-Path $env:LOCALAPPDATA 'ViralOS\Phase13'
if ([IO.Path]::GetFullPath($homeDir).StartsWith($root.TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Private workspace must be outside source' }
$venv=Join-Path $homeDir 'venv'
$py=Join-Path $venv 'Scripts\python.exe'
$env:VIRALOS_ENABLE_PRIVATE_UPLOAD='0'
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
$env:PYTHONNOUSERSITE='1'
Remove-Item Env:VIRALOS_INTERNAL_TEST_CLIENT -ErrorAction SilentlyContinue
function Run-Python { & $py @args; if ($LASTEXITCODE -ne 0) { throw "Python step failed ($LASTEXITCODE)" } }
Push-Location $root
try {
  if ($Mode -eq 'Setup') {
    if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw 'Install trusted Python 3.12 for Windows first' }
    if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue) -or -not (Get-Command ffprobe -ErrorAction SilentlyContinue)) { throw 'Install trusted FFmpeg and ffprobe on PATH first' }
    & py -3.12 tools/verify_package.py
    if ($LASTEXITCODE -ne 0) { throw 'Source integrity verification failed' }
    if (Test-Path $venv) { throw 'Environment exists; use Review/Pilot/Acceptance or manually choose a fresh environment after backup' }
    if ($Wheelhouse) {
      $Wheelhouse=(Resolve-Path -LiteralPath $Wheelhouse).Path
      if (-not (Test-Path -LiteralPath $Wheelhouse -PathType Container)) { throw 'Wheelhouse must be a directory' }
    } else {
      if ((Read-Host 'Install Python dependencies from configured pip index? Type INSTALL to approve') -cne 'INSTALL') { throw 'Installation declined' }
    }
    New-Item -ItemType Directory -Path $homeDir -Force | Out-Null
    & py -3.12 -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed' }
    if ($Wheelhouse) { Run-Python -m pip --disable-pip-version-check install --no-index --find-links $Wheelhouse --only-binary ':all:' -r requirements.txt }
    else { Run-Python -m pip --disable-pip-version-check install --only-binary ':all:' -r requirements.txt }
    Run-Python -m pip check
    Run-Python tools/check_environment.py
    & $py -m pip freeze | Set-Content -LiteralPath (Join-Path $homeDir 'installed-versions.txt') -Encoding UTF8
    if ($LASTEXITCODE -ne 0) { throw 'Dependency inventory failed' }
    Write-Host 'Setup complete. Use Start-Pilot.cmd with extracted pilot inputs.'
    return
  }
  if (-not (Test-Path -LiteralPath $py -PathType Leaf)) { throw 'Run Setup-ViralOS.cmd first' }
  Run-Python tools/verify_package.py
  Run-Python tools/check_environment.py
  if ($Mode -eq 'Acceptance') {
    $out=Join-Path $homeDir ('acceptance-'+[guid]::NewGuid().ToString('N'))
    & (Join-Path $PSScriptRoot 'run_windows_local_acceptance.ps1') -ReportDirectory $out -PythonExecutable $py
    if (-not $?) { throw 'Acceptance failed; inspect private report' }
    return
  }
  if ($Mode -eq 'Pilot') {
    $inputDir=Read-Host 'Absolute path to extracted pilot inputs (plan.json and assets folder)'
    $inputDir=(Resolve-Path -LiteralPath $inputDir).Path
    $run=Join-Path $homeDir ('pilot-'+[guid]::NewGuid().ToString('N'))
    Run-Python -m tools.pilot_pipeline build --plan (Join-Path $inputDir 'plan.json') --assets (Join-Path $inputDir 'assets') --output $run
    Write-Host "Private pilot run: $run"
  } else {
    $run=(Resolve-Path -LiteralPath (Read-Host 'Absolute path to an existing completed private pilot run')).Path
  }
  if ((Test-Path -LiteralPath (Join-Path $run 'INCOMPLETE')) -or -not (Test-Path -LiteralPath (Join-Path $run 'run.json'))) { throw 'Incomplete or missing pilot run' }
  Write-Host 'Open http://127.0.0.1:8765/ after server starts. Ctrl+C stops it. Never expose via LAN/tunnel.'
  Run-Python -m tools.domain_review_web --db (Join-Path $run 'reviews.sqlite') --catalog (Join-Path $run 'catalog.json') --port 8765
} finally { Pop-Location }
