# Duplo Player

**One video, two views.** A Windows 10/11 (64-bit) video player that decodes a single file and
shows it in one or two panes, each with its own zoom and rotation, but sharing the same frame,
clock, speed and audio.

*Português: veja [README.pt-BR.md](README.pt-BR.md). The app itself speaks English and Brazilian Portuguese.*

![Duplo Player with the screen split: playback is paused, a zoom rectangle is drawn on a face in the left view and on people far away in the right view, then both zoomed views play on in sync](docs/zoom-demo.gif)

<sub>Video: [Talha Uğuz / Pexels](https://www.pexels.com/video/vibrant-street-life-in-ankara-turkey-34892306/).</sub>

## What makes it different

- **The same video, twice, in two screens.** Ctrl+D plays one video in two views side by side, always in sync.
- **Zoom each screen on its own.** Drag a rectangle on either view to zoom into a detail while the other view
  keeps the whole picture (Ctrl+S turns the selection on; Ctrl+Z resets only the selected view).
- **Rotate with a simple command.** Ctrl+R turns the selected view 90° clockwise, and each view keeps its own rotation.
- **Record what you see.** Ctrl+G records the current screen (one or two views, with the zoom and rotation you chose,
  and the audio) to an MP4 file. Record several segments (beginning, middle, end…) and Ctrl+Shift+G joins them
  into a single video.
- **Delete videos from inside the player.** The trash button sends the video you are watching to the Windows Recycle Bin,
  after a confirmation, so you do not have to find it in its folder. It never deletes permanently.

## Highlights

- Synchronized dual view: one decoder, two independent crops.
- A–B loop, slow motion (0.1× to 0.75×) and speed-up to 2×.
- Real-time noise suppression, implemented in this project with NumPy (FFT).
- Recording of the composed view to MP4 (video + audio) through FFmpeg.
- Safe delete: uses the modern Windows API and refuses permanent deletion.
- Interface and instructions in English and Brazilian Portuguese.
- Unit tests, integration tests with the real VLC engine, and a written validation report (`VALIDATION.md`).

## Stack

Python 3.11 · PySide6 (Qt 6) · LibVLC / python-vlc · NumPy · FFmpeg (via imageio-ffmpeg) ·
pywin32 · Send2Trash · PyInstaller (packaging) · Inno Setup (installer) · `unittest`.

## Architecture

| Module | Responsibility |
|---|---|
| `main.py` | Entry point, arguments, start-up failure diagnostics, language selection |
| `duplo/engine.py` | LibVLC integration: receives frames through callbacks and hands the latest frame over as a `QImage` |
| `duplo/view.py` | Widget that paints the frame with its own crop (zoom) and rotation |
| `duplo/window.py` | Main window, shortcuts, playlist, update loop (~60 Hz) and preferences |
| `duplo/model.py` | Playlist (order, repeat, history) and A–B loop, with no interface dependency |
| `duplo/audio.py` | Receives PCM from VLC, applies volume and the filter, sends it to the sound device and to the recording |
| `duplo/noise.py` | Spectral noise reduction in overlapping blocks |
| `duplo/recording.py` | Composes the two views and encodes video + audio with FFmpeg |
| `duplo/explorer.py`, `duplo/recycle.py` | Windows integration: reveal the file in Explorer and move it to the Recycle Bin |
| `duplo/i18n.py` | Every user-facing string, as English / Portuguese pairs, with no Qt dependency |

## Install (if you just want to use it)

1. Open the **Releases** page of this repository and download `DuploPlayer-Setup-<version>.exe`
   (or the portable `.zip`, which needs no installation: extract it and run `DuploPlayer.exe`).
2. Run the installer. It installs for your user only and does not ask for administrator rights.
3. Open **Duplo Player** from the Start menu.

**Requirements:** Windows 10/11, 64-bit, and an audio device. You do not need to install Python, VLC,
FFmpeg or the Visual C++ Redistributable: everything ships inside the app.

> The installer is not digitally signed. Windows may show "Windows protected your PC" (SmartScreen):
> click *More info* and then *Run anyway*. If you would rather not trust a binary, use the option below
> and build the app yourself.
> The guide [`SECURITY.md`](SECURITY.md) shows how to check the installer (SHA256, VirusTotal,
> Windows Sandbox) and the scan result for this release.

### Make it the default video player

Windows does not let a program make itself the default, so it takes two steps. First offer Duplo Player
for every format it plays (current user only, nothing is installed):

```powershell
.\tools\register-file-types.ps1
```

The script then opens **Settings > Apps > Default apps** on Duplo Player's page: set it for the formats
you want (or choose it under "Open with" for a video, with "Always"). `-Exe <path>` registers another
copy; `-Remove` undoes the registration.

### Antivirus warnings

Executables built with PyInstaller and without a digital signature are sometimes flagged by a few
antivirus products as "suspicious" (generic or heuristic detections such as `Trojan:Win32/Wacatac` or
`Generic.ML`). This happens because PyInstaller bundles a Python interpreter that unpacks and loads the
program when it starts, which looks similar to how some malware behaves. It does not mean the file is infected.

To check it yourself:

1. Each release on **Releases** lists the installer's SHA256 and a link to the
   [VirusTotal](https://www.virustotal.com) analysis. Compare the hash of the file you downloaded:
   ```powershell
   Get-FileHash .\DuploPlayer-Setup-<version>.exe -Algorithm SHA256
   ```
2. If the hash matches, the VirusTotal analysis applies to your file. A few generic detections among
   dozens of antivirus engines are the false positive described above.
3. If you are still unsure, build the app from the source code (next section).

Result for version 1.0.0 (`DuploPlayer-Setup-1.0.0.exe`, SHA256 `38c8af8b…1393`): no engine flagged it,
0/66 in the [VirusTotal analysis](https://www.virustotal.com/gui/file/38c8af8bd63ba527d7bcc3ed3a51cec949a89c520a72c9ce5e0cdf9914a91393/detection)
of 2026-10-21 20:22 UTC.

![VirusTotal result for DuploPlayer-Setup-1.0.0.exe: 0 of 66 security vendors flagged the file](docs/virustotal-1.0.0.png)

## Run from source

**Prerequisites:** Windows 10/11 (64-bit), **Python 3.11 (64-bit)** with the *py launcher*
(included in the official installer from python.org), PowerShell, and internet access the first time
(to download the dependencies and portable VLC). Git is optional.

```powershell
git clone <repository-url>
cd duplo-player
.\setup.ps1                          # creates .venv, installs dependencies and downloads portable VLC (SHA256 checked)
.\.venv\Scripts\python.exe main.py   # opens the player
```

If PowerShell blocks scripts, run `Set-ExecutionPolicy -Scope Process Bypass` once in the same window.
You can also double-click `Iniciar.cmd`.

### Build the executable and the installer

```powershell
.\build.ps1        # produces dist\DuploPlayer\DuploPlayer.exe (portable version, uses PyInstaller)
.\installer.ps1    # produces dist-installer\DuploPlayer-Setup-<version>.exe (needs Inno Setup 6)
```

Inno Setup 6 is free: <https://jrsoftware.org/isdl.php>. The installer script is `installer/DuploPlayer.iss`.

### Publish a release (GitHub Actions)

The workflow `.github/workflows/build-windows.yml` runs on GitHub's Windows runners, follows the same steps
as above and attaches the installer and the portable `.zip` to the Releases page when you push a tag:

```powershell
git tag v1.0.0
git push origin v1.0.0
```

It can also be started by hand from the *Actions* tab (the result is then kept as a run artifact).

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v   # unit and interface tests
.\.venv\Scripts\python.exe tests\integration.py              # integration with real VLC (synthetic videos)
```

The integration tests create synthetic videos in `test-output/` (ignored by git).
See the result and the limits of the validation in `VALIDATION.md`.

## Interface language

The app speaks English and Brazilian Portuguese. At start-up it uses, in this order:

1. the `DUPLO_LANG` environment variable (`en` or `pt`);
2. the language you chose before: right-click the image and pick **Idioma / Language**;
3. your Windows language and region setting (Portuguese if it is Portuguese, English otherwise).

A language chosen from the menu applies the next time you open the app. The installer also offers both languages.
All text lives in `duplo/i18n.py`, and `tests/test_i18n.py` checks that every string exists in both languages.

## How it was built (with AI)

I built this project by guiding AI coding assistants through prompts (vibe coding): I described the
behaviour I wanted, tested it, pointed out defects and asked for fixes. That is why the repository puts
so much weight on tests and written validation: they were how I checked that the requested behaviour
really worked. The known limits are listed below and in `VALIDATION.md`.

## Known limits

- Windows only (uses pywin32, Explorer and the Windows Recycle Bin).
- Recordings are saved to `C:\Videos\trechos` and joined videos to `C:\Videos\joined`, paths fixed in the code.
- The tests use short synthetic videos; 4K/8K and every codec profile have not been certified.

## License

The Duplo Player source code is released under the [MIT License](LICENSE), copyright (c) 2026 Marcos Amorim.
The MIT License covers this project's own code only. The bundled components (VLC, FFmpeg, Qt and others)
keep their own licenses.

## Third-party licenses

See `THIRD-PARTY.md` and the `licenses/` folder. VLC and FFmpeg are not stored in the repository:
VLC is downloaded by `setup.ps1` and FFmpeg comes from the `imageio-ffmpeg` package.
The binaries published on Releases include those components; the corresponding FFmpeg and VLC
source code is available from the projects' websites (links in `THIRD-PARTY.md`).

---

## User guide

### Features

- Right-click the image: open the folder with the playing video selected in Explorer,
  using the native Windows identity (including spaces, commas and accents);
  move the video to the Recycle Bin, always with a confirmation whose default is Cancel.
- All controls sit below the video. Hover over the icons to see what they do and their shortcut.
- The order icon cycles **Sequential → Random video → Shuffle list**.
  Random video picks another item on every advance and may revisit files.
  Shuffle list shuffles without repeating items within the same cycle.
- The repeat icon cycles **No repeat → Repeat video → Repeat list**.
  Order and repeat are independent. With no repeat, the random modes stop after one cycle
  as long as the list; random video may revisit files during that cycle. Repeat list allows new cycles.
  Repeat video keeps the current file. When the same video repeats, both zooms, the split,
  full screen and the speed are preserved.
- A–B loop: press **3** to set start A; move forward and press **3** again to set end B and loop the range.
  Another press of **3** starts a new range. **A** and **B** can also be used separately.
  B must be at least 0.1 s after A. Clear A–B turns the range off.
  A–B takes priority over the repeat modes and is cleared when the file changes.
- Zoom: press **Ctrl+S** (or **Z**), then click and drag a rectangle on the image.
  It works in windowed mode and in full screen, in each pane of the split.
  Press **Ctrl+S** again to turn the selection off.
  The selected region is enlarged keeping its aspect ratio. You can zoom again on the current crop.
  Bars outside the picture are not part of the selection.
- Split screen: **Ctrl+D** (or **D**) turns on the dual view; press it again to turn it off, also in full screen.
  Each view accepts a different crop. Click one to select it and use **Ctrl+Z** (or **R**) to reset only its zoom.
- Independent rotation: **Ctrl+R** rotates the selected view 90° clockwise:
  **0° → 90° → 180° → 270° → 0°**. Click the pane you want before rotating.
  It works in full screen, with zoom and in recordings; repeating the video keeps the rotation.
- True full screen: **F11** or a double-click shows only the video, with no buttons, titles or list.
  The split and the zoom crops are preserved. **Esc** returns to windowed mode.
  Shortcuts and the right-click menu keep working. Move the mouse to the bottom of the screen to show a
  floating timeline (click or drag to seek); it hides again when the mouse leaves it and never enters recordings.
- Slow motion from **0.1× to 0.75×**, normal speed and speed-up to **2×**.
  The **-** key lowers the speed in steps: **0.75× → 0.5× → 0.25×**, also in full screen.
  The **+** key raises the speed, passing through **1×** and speeding up to **2×**.
  **E** pauses and steps one frame. Audio may be affected at extreme speeds.

### Noise suppression

The noise icon in the bottom panel turns the filter on and off. Adjust the **0 to 100%** bar next to the
icon: 0% keeps the original audio; 100% applies the filter's maximum reduction. **Ctrl+H** toggles the
filter, also in full screen; the right-click menu offers the same strength bar.

The filter adapts the reduction to background hiss and keeps the stereo image. The effect applies to
playback and recording, with a single audio track for both views. Lower strengths keep more detail;
higher ones remove more noise. Volume, speed, zoom and rotation keep working. The strength is saved when
you close the app, but the suppressor always starts **off** when the player opens.

### Recording

Click the red circle or press **Ctrl+G** to start, and again to stop. The MP4 is saved automatically to
**C:\Videos\trechos**, named after the video being played: `video name_T1.mp4`, then `_T2`, `_T3` and so on for
more recordings of the same video. In full screen, use Ctrl+G or the recording option in the
right-click menu. While recording, a blinking **● REC** badge with the recorded time shows in the top-right
corner of the video, also in full screen; it is only on screen and never appears in the recording.

The recording contains the displayed video and its audio, without controls, titles, cursor, list or other
applications. Split views appear side by side, each with its own zoom. Changes of split, zoom, rotation,
speed, seeking and repeat are captured. When paused, the picture freezes and the audio goes silent.
When you close the player, the recording is finished before it exits.

The resolution is set at the start, capped at 1920×1080, at 30 frames/s with stereo AAC audio. Resizing
the window keeps the aspect ratio using black bars. While recording, temporary files live in their own
folder inside C:\Videos\trechos; they are removed once the recording is finished. If something fails they are kept
so you can recover them. Wait for the **Recording saved** message before opening the file.

#### Several segments in one video

Each Ctrl+G start/stop records one segment, saved as its own MP4 as above. Record as many as you like, for
example one at the beginning, one in the middle and one at the end, even across different videos. Then press
**Ctrl+Shift+G** (or the join button next to the record button, or the right-click menu) to join them, in
recording order, into one new `video name_joined.mp4` in **C:\Videos\joined** (named after the first segment's
video; `_joined_2`, `_joined_3`… if that name exists). If a segment is still recording, it is finished
first and becomes the last part. The join copies the streams without re-encoding, so it is fast and keeps the
quality: every segment after the first uses the first one's resolution, with black bars if the window changed
size. The join only creates a new file: the segment recordings are kept as they are. Only the join's own
temporary files are deleted, and a joined file that fails or comes out shorter than the segments is discarded.
At least two segments are needed.

### Shortcuts

| Key | Action |
|---|---|
| Ctrl+O / Ctrl+Shift+O | Open videos / folder |
| Space | Pause / resume |
| Ctrl+S / Z | Turn selection zoom on/off, also in full screen |
| Ctrl+Z / R | Reset only the selected view's zoom |
| Shift+R | Reset both zooms |
| Ctrl+R | Rotate the selected view 90° clockwise |
| Ctrl+G | Start / stop recording (one segment) |
| Ctrl+Shift+G | Join the recorded segments into one video |
| Ctrl+D / D | Turn the dual view on / off, also in full screen |
| 3 | Set A, then B; with an active range, start a new one |
| A / B / C | Set A / set B / clear A–B |
| - | Slow motion in steps: 0.75× → 0.5× → 0.25×; works on the numeric keypad |
| + | Speed up to 2×, passing through 1×; works on the numeric keypad |
| [ / ] | Decrease / increase speed |
| E | Pause and step one frame |
| ← / → | Rewind / forward 5 seconds |
| ↑ / ↓ | Volume up / down in 5% steps; turning it up also unmutes |
| 1 / 2 | Previous / next video |
| N / P / S | Next / previous / stop |
| M | Mute |
| Ctrl+H | Turn noise suppression on / off |
| F11 / double-click the image | Full screen: video only, keeping the split |
| Esc | Leave full screen; in windowed mode, cancel zoom selection |
| Ctrl+L | Show / hide the list in windowed mode |
| F1 | Help |

### Formats and limits

The VLC engine accepts the main containers and codecs, including MP4, MKV, AVI, MOV, WMV, WebM, FLV,
MPEG, TS/M2TS, VOB, OGV and 3GP, with codecs such as H.264, H.265/HEVC, MPEG-4, VP8/VP9 and AV1.
Real support depends on the codec, profile, file integrity and the computer's performance. DRM is not supported.

This version duplicates **the same file**; it does not compare two different files.
Zoom is digital; it does not create detail that is missing from the original picture.
The shared output uses CPU decoding so that both crops are possible.
4K/8K videos or those with many frames per second may need more processing power.
Seek and A–B precision depend on the codec and on the file's key frames.

The Recycle Bin uses the modern Windows API and refuses permanent-delete operations.
Only fixed local drives are accepted. Network files, USB drives and cases where Windows does not offer
recycling are refused. There is no fallback to delete permanently. If the move fails, the player shows the error.
