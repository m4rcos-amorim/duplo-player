$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    py -3.11 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Install 64-bit Python 3.11 before continuing.' }
}
& '.\.venv\Scripts\python.exe' -m pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw 'Failed to install the dependencies.' }
if (-not (Test-Path -LiteralPath 'vendor\vlc\libvlc.dll')) {
    New-Item -ItemType Directory -Path 'downloads','vendor' -Force | Out-Null
    $vlcUrl = 'https://download.videolan.org/pub/videolan/vlc/3.0.24/win64/vlc-3.0.24-win64.zip'
    Invoke-WebRequest -Uri $vlcUrl -OutFile 'downloads\vlc.zip'
    Invoke-WebRequest -Uri ($vlcUrl + '.sha256') -OutFile 'downloads\vlc.sha256'
    $vlcHash = ((Get-Content -LiteralPath 'downloads\vlc.sha256' -Raw) -split '\s+')[0]
    if ((Get-FileHash -LiteralPath 'downloads\vlc.zip' -Algorithm SHA256).Hash -ine $vlcHash) {
        throw 'The SHA256 check of VLC failed.'
    }
    Expand-Archive -LiteralPath 'downloads\vlc.zip' -DestinationPath 'vendor'
    Move-Item -LiteralPath 'vendor\vlc-3.0.24' -Destination 'vendor\vlc'
}
Write-Output 'Done. Run Iniciar.cmd to open Duplo Player.'
