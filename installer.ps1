# Builds the installer DuploPlayer-Setup-<version>.exe from dist\DuploPlayer.
# Usage:  .\build.ps1   (produces dist\DuploPlayer)
#       .\installer.ps1 [-Version 1.0.0]
param([string]$Version = '1.0.0')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath 'dist\DuploPlayer\DuploPlayer.exe')) {
    throw 'Run .\build.ps1 first: dist\DuploPlayer\DuploPlayer.exe does not exist.'
}
$candidates = @(
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
)
$iscc = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $iscc) {
    $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($cmd) { $iscc = $cmd.Source }
}
if (-not $iscc) { throw 'Inno Setup 6 was not found. Install it from https://jrsoftware.org/isdl.php and run this again.' }
& $iscc "/DAppVersion=$Version" 'installer\DuploPlayer.iss'
if ($LASTEXITCODE -ne 0) { throw 'Building the installer failed.' }
Write-Output (Join-Path $PSScriptRoot "dist-installer\DuploPlayer-Setup-$Version.exe")
