# Story 2.13: Silently install GraceTree Shorts Studio on Windows.
#
# Usage:
#   .\install.ps1 -InstallerPath "C:\path\to\setup.exe"
#
# The installer is run with /S (NSIS silent mode) and the script waits for
# completion, then verifies the install directory was created.

param(
  [Parameter(Mandatory = $true)]
  [string]$InstallerPath
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $InstallerPath)) {
  Write-Error "Installer not found: $InstallerPath"
  exit 1
}

Write-Host "[install] Running installer: $InstallerPath"
$proc = Start-Process -FilePath $InstallerPath -ArgumentList '/S' -PassThru -Wait
if ($proc.ExitCode -ne 0) {
  Write-Error "Installer exited with code $($proc.ExitCode)"
  exit 1
}

# Verify install directory
$installDir = "$env:LOCALAPPDATA\Programs\GraceTree Shorts Studio"
if (-not (Test-Path $installDir)) {
  Write-Error "Install directory not found: $installDir"
  exit 1
}

Write-Host "[install] OK — installed to $installDir"
