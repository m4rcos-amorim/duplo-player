# Security: how to verify Duplo Player

Portuguese version: [SEGURANCA.md](SEGURANCA.md).

If you are wary of downloading an `.exe` from the internet, you are right to be. This guide shows how to check
the installer yourself, without having to trust me. The steps go from the quickest to the most thorough.

## What has been checked

The SHA256 and the VirusTotal report of each installer are published in the **notes of its Release**, not in this
file. The hash changes with every build, and this file ships inside the installer, so it cannot contain the hash of
the file that carries it. The Release notes also say when the scan was done.

| Item | Where to look |
|---|---|
| SHA256 of the installer | Release notes (and Step 1 below) |
| VirusTotal result | Link in the Release notes (and Step 2 below) |
| Digital signature | **Not signed.** That is why Windows (SmartScreen) shows a warning the first time you run it |

Some VirusTotal engines may not answer in time and a few do not analyse this file type. A result applies only
to the file with that exact SHA256. If the hash of your file is different, it is not the same file and you
should repeat the verification.

## What the program does (and does not do)

- It is a local video player: it opens files from your computer, plays them with the embedded VLC and,
  if you ask, records the player's view to `C:\Videos` using FFmpeg.
- The application's Python code **contains no network calls** (no `urllib`, `requests` or `socket`)
  and has no telemetry. The only external program it starts is FFmpeg, to record.
  Check it yourself, in the source folder:

  ```powershell
  Select-String -Path main.py, duplo\*.py -Pattern 'urllib|requests|socket|http'
  ```

  (The only expected match is the SVG namespace address in `duplo\icons.py`.)
- The trash button only moves files to the Windows Recycle Bin and asks for confirmation; it never deletes permanently.
- The installation is per user and **does not ask for administrator rights**.

## Step 1: check that it is the same file (SHA256)

In PowerShell, in the folder where you downloaded the installer:

```powershell
Get-FileHash .\DuploPlayer-Setup-1.0.0.exe -Algorithm SHA256
```

The value must match the one in the Release notes. If it differs,
**do not run** the file.

## Step 2: check on VirusTotal

Two ways, at <https://www.virustotal.com>:

- **By hash (without uploading the file):** paste the SHA256 into the search box. If the file has already
  been analysed, the report appears.
- **Uploading the file:** use the *File* tab and drag the installer in.

How to read it: one or two alerts from little-known engines, with generic names such as "Generic" or "Heur",
are common for programs built with PyInstaller without a signature. Many alerts, or alerts from major antivirus
products, are a reason not to install and to open an *issue* here.

## Step 3: check the digital signature

```powershell
Get-AuthenticodeSignature .\DuploPlayer-Setup-1.0.0.exe | Format-List Status, SignerCertificate
```

The expected result today is `NotSigned`. It means the installer has no signature from a code-signing
certificate (those certificates are paid for and this is a personal project). A signature would prove who
published it; its absence does not, by itself, indicate a virus.

## Step 4: scan with Microsoft Defender

```powershell
Start-MpScan -ScanType CustomScan -ScanPath "$env:USERPROFILE\Downloads\DuploPlayer-Setup-1.0.0.exe"
Get-MpThreatDetection | Select-Object -First 5
```

If nothing was detected, `Get-MpThreatDetection` shows nothing related to the file. You can also right-click
the installer and choose *Scan with Microsoft Defender*.

## Step 5: install in an isolated environment

If you want to test without risking your computer:

- **Windows Sandbox** (Windows 10/11 Pro, Enterprise or Education; turn it on under *Turn Windows features
  on or off*). Save the file below as `duplo-test.wsb` and double-click it. The Sandbox opens with no network
  and sees only your downloads folder, read-only. Replace `YOUR_USER` with your user name:

  ```xml
  <Configuration>
    <Networking>Disable</Networking>
    <MappedFolders>
      <MappedFolder>
        <HostFolder>C:\Users\YOUR_USER\Downloads</HostFolder>
        <ReadOnly>true</ReadOnly>
      </MappedFolder>
    </MappedFolders>
  </Configuration>
  ```

  Inside the Sandbox, run the installer from the mapped folder. Everything is erased when you close the window.
- **Virtual machine** (VirtualBox, VMware, Hyper-V) with a test Windows 10/11 and no shared folders.

## Step 6: watch what the program does while it runs

With Duplo Player open, see whether it has network connections:

```powershell
Get-NetTCPConnection -OwningProcess (Get-Process DuploPlayer).Id -ErrorAction SilentlyContinue
```

No output means it has no active TCP connections. For a more detailed analysis, use Microsoft Sysinternals'
*Process Monitor* and *TCPView* (<https://learn.microsoft.com/sysinternals/>), filtering by the
`DuploPlayer.exe` process.

## Step 7: build the app yourself (the strongest proof)

Instead of trusting the binary, compile from source and use your own result:

```powershell
git clone <repository-url>
cd duplo-player
.\setup.ps1      # Python 3.11 (64-bit); downloads dependencies and portable VLC (VLC's SHA256 is checked)
.\build.ps1      # produces dist\DuploPlayer\DuploPlayer.exe
```

The details are in `README.md`. The hash of your build **will differ** from the published one, because
PyInstaller builds are not reproducible byte for byte. What matters is that it comes from code you can read.
The binaries on Releases can also be produced by the public workflow `.github/workflows/build-windows.yml`,
whose log shows every build step.

## Step 8: read the code

The code is small (about 2,500 lines in the `duplo/` package) and is described in `README.md`, under
*Architecture*. The places that matter most to a cautious reader:

- `duplo/recording.py`: the only place that starts an external program (FFmpeg).
- `duplo/recycle.py` and `duplo/explorer.py`: the only Windows integrations (Recycle Bin and opening a folder).
- `THIRD-PARTY.md`: the list of bundled third-party components (VLC, FFmpeg, Qt, NumPy) and their licenses.

## If something looks wrong

- Do not run the installer, and open an *issue* in this repository with the result of Step 1 and Step 2.
  If you found a security vulnerability, do not publish exploit details in the issue: use GitHub's
  private vulnerability reporting for this repository if it is enabled, or ask in the issue for a private channel.
- To remove an existing installation: *Settings > Apps > Installed apps > Duplo Player > Uninstall*.
  Recordings in `C:\Videos` are not deleted by the uninstaller.
- If your antivirus flags the file as suspicious, most vendors accept the file as a false-positive
  submission for re-analysis.
