# ViralOS M4 Windows i7/32GB acceptance preflight: read-only system checks.
# No installation, OAuth access, external network, YouTube upload or Git action.
param([string]$ReportPath = "")
$ErrorActionPreference = 'Stop'
if (-not $IsWindows -and $PSVersionTable.PSEdition -eq 'Core') { throw 'Run on the owner Windows 10/11 machine' }
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not $ReportPath) {
  $ReportPath = Join-Path $root 'reports\windows_preflight_local.json'
}
if (Test-Path $ReportPath) { throw 'Refusing to overwrite existing report: choose a new ReportPath' }
$computer = Get-CimInstance Win32_ComputerSystem
$os = Get-CimInstance Win32_OperatingSystem
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$ramGiB = [math]::Round([double]$computer.TotalPhysicalMemory / 1GB, 2)
$py = Get-Command py -ErrorAction SilentlyContinue
$ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
$ffprobe = Get-Command ffprobe -ErrorAction SilentlyContinue
$checks = [ordered]@{
  'windows_10_11' = [bool]($os.Caption -match 'Windows (10|11)')
  'memory_gte_28gib' = ($ramGiB -ge 28)
  'python_launcher_present' = [bool]$py
  'ffmpeg_available' = [bool]$ffmpeg
  'ffprobe_available' = [bool]$ffprobe
  'devanagari_font_available' = [bool](Test-Path "$env:WINDIR\Fonts\Nirmala.ttf") -or [bool](Test-Path "$env:WINDIR\Fonts\Mangal.ttf")
}
$version = 'UNKNOWN'
if ($py) {
  try { $version = (& py -3.12 --version 2>&1 | Out-String).Trim() } catch { $version = 'Python 3.12 NOT FOUND' }
}
$checks['python_312_usable'] = $version -match '^Python 3\.12\.'
$report = [ordered]@{
  stage = 'M4_WINDOWS_OWNER_ACCEPTANCE_PREFLIGHT'
  timestamp_utc = [datetime]::UtcNow.ToString('o')
  operating_system = $os.Caption
  cpu_model = $cpu.Name
  physical_ram_gib = $ramGiB
  python_312 = $version
  checks = $checks
  passed = -not ($checks.Values -contains $false)
  performance_benchmark_tested = $false
  actual_ffmpeg_render_playback_tested = $false
  audio_listening_tested = $false
  restart_persistence_tested = $false
  owner_acceptance = 'PENDING_REAL_WINDOWS_SESSION'
  network_calls_made = $false
}
$folder=Split-Path -Parent $ReportPath
if (-not (Test-Path $folder)) { New-Item -ItemType Directory -Path $folder -Force | Out-Null }
$report | ConvertTo-Json -Depth 8 | Set-Content -Path $ReportPath -Encoding UTF8
Write-Host "ViralOS Windows preflight report: $ReportPath"
$report.checks | Format-Table
if (-not $report.passed) { exit 2 }
