# Offer Duplo Player for the video formats it plays, for the current user only.
#
# Windows does not let a program make itself the default: after running this,
# choose Duplo Player in Settings > Apps > Default apps (the script opens it).
# Nothing outside HKCU is touched. Undo with -Remove.
#
#   .\tools\register-file-types.ps1                 # register dist\DuploPlayer\DuploPlayer.exe
#   .\tools\register-file-types.ps1 -Exe 'C:\...\DuploPlayer.exe'
#   .\tools\register-file-types.ps1 -Remove
param(
    [string]$Exe = (Join-Path $PSScriptRoot '..\dist\DuploPlayer\DuploPlayer.exe'),
    [switch]$Remove,
    [switch]$NoSettings
)
$ErrorActionPreference = 'Stop'

# Keep in sync with EXTENSIONS in duplo/model.py (checked by tests/test_file_types.py).
$Extensions = @('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.webm', '.flv', '.m4v',
                '.mpg', '.mpeg', '.ts', '.mts', '.m2ts', '.vob', '.ogv', '.3gp',
                '.3g2', '.divx', '.asf', '.rm', '.rmvb', '.mxf', '.av1')

$ProgId = 'DuploPlayer.Video'
$AppName = 'Duplo Player'
$Classes = 'HKCU:\Software\Classes'
$CapabilitiesPath = 'Software\DuploPlayer\Capabilities'

function Set-Default([string]$Path, [string]$Value) {
    New-Item -Path $Path -Force | Out-Null
    Set-Item -Path $Path -Value $Value
}

function Send-AssociationChanged {
    Add-Type -Namespace Duplo -Name Shell -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("shell32.dll")]
public static extern void SHChangeNotify(int eventId, uint flags, System.IntPtr item1, System.IntPtr item2);
'@
    [Duplo.Shell]::SHChangeNotify(0x08000000, 0, [IntPtr]::Zero, [IntPtr]::Zero)  # SHCNE_ASSOCCHANGED
}

if ($Remove) {
    foreach ($ext in $Extensions) {
        $key = "$Classes\$ext\OpenWithProgids"
        if (Test-Path $key) { Remove-ItemProperty -Path $key -Name $ProgId -ErrorAction SilentlyContinue }
    }
    foreach ($key in "$Classes\$ProgId", "$Classes\Applications\DuploPlayer.exe", 'HKCU:\Software\DuploPlayer',
                     'HKCU:\Software\Microsoft\Windows\CurrentVersion\App Paths\DuploPlayer.exe') {
        if (Test-Path $key) { Remove-Item -Path $key -Recurse -Force }
    }
    Remove-ItemProperty -Path 'HKCU:\Software\RegisteredApplications' -Name $AppName -ErrorAction SilentlyContinue
    Send-AssociationChanged
    Write-Output "Duplo Player removed from the video file types."
    return
}

$Exe = (Resolve-Path -LiteralPath $Exe).Path
$command = "`"$Exe`" `"%1`""

# One file type (ProgID) for every video format.
Set-Default "$Classes\$ProgId" 'Vídeo (Duplo Player)'
Set-ItemProperty -Path "$Classes\$ProgId" -Name 'FriendlyTypeName' -Value 'Vídeo (Duplo Player)'
Set-Default "$Classes\$ProgId\DefaultIcon" "`"$Exe`",0"
Set-Default "$Classes\$ProgId\shell\open\command" $command
New-ItemProperty -Path "$Classes\$ProgId\shell\open" -Name 'FriendlyAppName' -Value $AppName -PropertyType String -Force | Out-Null
# Name and icon shown in "Open with" and Default apps (the exe has no version resource).
New-Item -Path "$Classes\$ProgId\Application" -Force | Out-Null
Set-ItemProperty -Path "$Classes\$ProgId\Application" -Name 'ApplicationName' -Value $AppName
Set-ItemProperty -Path "$Classes\$ProgId\Application" -Name 'ApplicationIcon' -Value "`"$Exe`",0"

# A choice saved as "Applications\DuploPlayer.exe" (picked by browsing to an exe) did not
# start the player on Windows 11 and kept pointing at a removed copy. Drop that entry so
# Windows offers the ProgID above, and point the exe name at this copy.
if (Test-Path "$Classes\Applications\DuploPlayer.exe") { Remove-Item "$Classes\Applications\DuploPlayer.exe" -Recurse -Force }
$appPath = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\App Paths\DuploPlayer.exe'
Set-Default $appPath $Exe
Set-ItemProperty -Path $appPath -Name 'Path' -Value (Split-Path $Exe)

# Capabilities make Duplo Player appear in Settings > Default apps.
$capabilities = "HKCU:\$CapabilitiesPath"
New-Item -Path "$capabilities\FileAssociations" -Force | Out-Null
Set-ItemProperty -Path $capabilities -Name 'ApplicationName' -Value $AppName
Set-ItemProperty -Path $capabilities -Name 'ApplicationDescription' -Value 'Um vídeo, duas perspectivas. / One video, two views.'
Set-ItemProperty -Path $capabilities -Name 'ApplicationIcon' -Value "`"$Exe`",0"
New-Item -Path 'HKCU:\Software\RegisteredApplications' -Force | Out-Null
Set-ItemProperty -Path 'HKCU:\Software\RegisteredApplications' -Name $AppName -Value $CapabilitiesPath

foreach ($ext in $Extensions) {
    New-Item -Path "$Classes\$ext\OpenWithProgids" -Force | Out-Null
    New-ItemProperty -Path "$Classes\$ext\OpenWithProgids" -Name $ProgId -PropertyType String -Value '' -Force | Out-Null
    Set-ItemProperty -Path "$capabilities\FileAssociations" -Name $ext -Value $ProgId
}
Send-AssociationChanged
Write-Output "Duplo Player registered for $($Extensions.Count) video formats: $Exe"
if (-not $NoSettings) {
    # The final choice is the user's: open Default apps on Duplo Player's page.
    Start-Process "ms-settings:defaultapps?registeredAppUser=$([uri]::EscapeDataString($AppName))"
}
