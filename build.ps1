$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonExe = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$buildOriginalPath = $env:PATH
try {
    # Isolate DLL discovery from other apps such as Poppler on the host PATH.
    $env:PATH = "$PSScriptRoot\.venv\Scripts;$env:SystemRoot\System32;$env:SystemRoot"
    & $pythonExe -m PyInstaller --noconfirm --windowed --onedir --collect-all imageio_ffmpeg --name DuploPlayer --icon 'assets\duplo.ico' --add-data 'assets;assets' --add-data 'vendor\vlc;vendor\vlc' --hidden-import 'win32com.shell.shell' --hidden-import 'pythoncom' --hidden-import 'pywintypes' --exclude-module 'PySide6.QtWebEngineCore' --exclude-module 'PySide6.QtWebEngineWidgets' --exclude-module 'PySide6.QtQml' --exclude-module 'PySide6.QtQuick' main.py
} finally {
    $env:PATH = $buildOriginalPath
}
if ($LASTEXITCODE -ne 0) { throw 'The build failed.' }
# Qt on Windows uses the OS ICU API. A third-party icuuc.dll with versioned
# exports is incompatible; never ship that name at the application root.
$bundledIcu = Join-Path $PSScriptRoot 'dist\DuploPlayer\_internal\icuuc.dll'
if (Test-Path -LiteralPath $bundledIcu) { Remove-Item -LiteralPath $bundledIcu -Force }
# Use the runtime shipped with Qt consistently, also for the Python bootloader.
$qtRuntime = Join-Path $PSScriptRoot '.venv\Lib\site-packages\PySide6'
foreach ($runtimeFile in @('vcruntime140.dll','vcruntime140_1.dll','msvcp140.dll','msvcp140_1.dll','msvcp140_2.dll','msvcp140_codecvt_ids.dll','concrt140.dll')) {
    Copy-Item -LiteralPath (Join-Path $qtRuntime $runtimeFile) -Destination 'dist\DuploPlayer\_internal' -Force
}
Copy-Item -LiteralPath 'LICENSE','README.md','README.pt-BR.md','THIRD-PARTY.md','THIRD-PARTY.pt-BR.md','VALIDATION.md','VALIDACAO.md','SECURITY.md','SEGURANCA.md' -Destination 'dist\DuploPlayer'
Copy-Item -LiteralPath 'licenses' -Destination 'dist\DuploPlayer' -Recurse -Force
Write-Output (Join-Path $PSScriptRoot 'dist\DuploPlayer\DuploPlayer.exe')
