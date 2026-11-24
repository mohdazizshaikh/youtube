# Owner-run LOCAL Windows acceptance bundle. No OAuth, remote access, push or installation.
# Example: .\tools\run_windows_local_acceptance.ps1 -ReportDirectory C:\Private\ViralOS-Acceptance-20261124
param([Parameter(Mandatory=$true)][string]$ReportDirectory, [string]$PythonExecutable="")
$ErrorActionPreference='Stop'
if (-not $IsWindows -and $PSVersionTable.PSEdition -eq 'Core') { throw 'Windows owner PC required' }
$root=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$out=[IO.Path]::GetFullPath($ReportDirectory)
if ($out -eq $root -or $out.StartsWith($root.TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase)) {
  throw 'Acceptance evidence must live OUTSIDE source repository'
}
if (Test-Path $out) { throw 'Choose a NEW report directory, never overwrite evidence' }
New-Item -ItemType Directory -Path $out -Force | Out-Null
# Never let regression tests open or mutate a real owner database.
$env:VIRALOS_DB=Join-Path $out 'pytest-only-synthetic.sqlite'
$env:VIRALOS_ENABLE_PRIVATE_UPLOAD='0'
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
if ($PythonExecutable) {
  $py=(Resolve-Path -LiteralPath $PythonExecutable).Path
  $pythonArgs=@()
} else {
  $py=Get-Command py -ErrorAction Stop
  $pythonArgs=@('-3.12')
}
$results=[ordered]@{}
Push-Location $root
try {
  & powershell.exe -NoProfile -File (Join-Path $PSScriptRoot 'windows_acceptance.ps1') -ReportPath (Join-Path $out 'hardware-preflight.json') *> (Join-Path $out 'hardware-preflight.log')
  $results['windows_preflight_exit']=$LASTEXITCODE
  & $py @pythonArgs tools/offline_acceptance_drill.py --json-out (Join-Path $out 'synthetic-backup-restore.json') *> (Join-Path $out 'synthetic-backup-restore.log')
  $results['synthetic_recovery_exit']=$LASTEXITCODE
  & $py @pythonArgs -m pytest -q *> (Join-Path $out 'pytest.log')
  $results['pytest_exit']=$LASTEXITCODE
  & $py @pythonArgs tools/verify_package.py *> (Join-Path $out 'package-hashes.log')
  $results['integrity_exit']=$LASTEXITCODE
  & $py @pythonArgs tools/studio_smoke.py *> (Join-Path $out 'cpu-studio-smoke.log')
  $results['cpu_render_exit']=$LASTEXITCODE
  & $py @pythonArgs -m compileall -q app tools tests *> (Join-Path $out 'python-compile.log')
  $results['python_compile_exit']=$LASTEXITCODE
  $node=Get-Command node -ErrorAction SilentlyContinue
  if ($node) {
    & node --check app/static/app.js *> (Join-Path $out 'javascript-syntax.log')
    $results['javascript_syntax_exit']=$LASTEXITCODE
  } else {
    $results['javascript_syntax_exit']='NOT_AVAILABLE'
  }
} finally {
  Pop-Location
}
$passed=$true
foreach ($value in $results.Values) { if ($value -ne 0) { $passed=$false } }
$report=[ordered]@{
  schema='VIRALOS_LOCAL_WINDOWS_ENGINEERING_ACCEPTANCE_V1'
  timestamp_utc=[datetime]::UtcNow.ToString('o')
  checks=$results
  local_checks_passed=$passed
  actual_user_hardware_used=$true
  account_oauth_tested=$false
  live_youtube_upload_tested=$false
  licensed_voices_and_nativespeaker_listening_tested=$false
  complete_owner_disaster_restore_tested=$false
  owner_final_acceptance='PENDING_SUPERVISED_REVIEW'
  external_network_requested_by_this_script=$false
}
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $out 'result.json') -Encoding UTF8
Write-Host "ViralOS local acceptance evidence: $out"
if (-not $passed) { exit 2 }
