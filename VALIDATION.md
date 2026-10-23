# Validation — October 4, 2026

Portuguese version (original log): `VALIDACAO.md`. The sections below are a translation of it,
followed by a note about the interface languages.

Project: Duplo Player. 64-bit Windows 11; Python 3.11;
PySide6 6.11.2; LibVLC 3.0.24; PyInstaller 6.22.3.

## Results

- **9 unit tests passed**: playlist, no-repeat shuffle within a cycle,
  end of list, repeat video/list, history, item removal and A–B validation.
- **25 integration checks passed** with the real VLC.
  Videos and audio are synthetic, created only for the test.
- Playback validated on MP4/H.264, MKV, AVI/MPEG-4, MOV, WebM/VP9,
  WMV, MPEG-2, TS, FLV, MP4/HEVC and MKV/AV1.
- Correct aspect ratios verified at 960×540 and 320×180, including MPEG/TS.
- Same QImage in both views across 20 playback samples.
- Selection with real mouse events, independent crops, rejection of a
  selection outside the frame, and reset of only one view.
- Pause, frame step and resume; 0.25× slow motion advancing about
  250 ms of media in 1.2 s once seeking settled.
- A–B returned to A twice during sampling; repeat video, list advance
  and return to the start in repeat-list mode passed.
- The Explorer command was checked with a mock; the Explorer window itself was not automated.
- Confirmation cancelled: file kept and playback resumed.
- Simulated recycle failure: file kept and playback resumed.
- A real move to the Recycle Bin passed using a disposable copy created in
  `test-output`, without touching the synthetic source video or any personal video.
- **Portable executable passed**: starts without an external Python, decodes
  the video, splits the screen, applies different zooms, accepts 0.5× speed,
  initializes the Recycle Bin COM API and exits with code 0.

## Evidence

- `test-output/integration-results.json` and `integration.log`.
- `test-output/duas-perspectivas.png` and `player-inicial.png`.
- `test-output/packaged-smoke/packaged-smoke.json` and `player-preview.png`.

The package was reviewed visually with the fonts installed on Windows.
The build isolates DLL lookup from other programs' PATH entries and uses
the native Windows ICU. No system library was installed or replaced.

## Limits of the validation

The tests use short synthetic files. They do not certify every codec profile
or performance on 4K/8K videos. Synchronization of the views is guaranteed by
sharing the same frame. Seek/A–B precision still depends on the codec and
key frames. Real audio playback was not assessed by listening. DRM is not supported.


## Update: interface and shortcuts

- 14 tests passed: the 9 model tests and 5 interface tests.
- List hidden on open; Ctrl+L available only in windowed mode.
- Full screen shows only the video, with no controls, titles, borders or margins.
- Split and independent zooms preserved when entering/leaving full screen.
- F11, Esc, D and Z verified with real keyboard events.
- Arrow keys rewind/forward 5 seconds even when the volume or speed control has focus.
- 1/2 go to the previous/next video in windowed mode and in full screen.
- Interface capture: test-output/fullscreen-ui.png.
- The executable test also checks split full screen, no controls/list, and that the
  zooms are preserved when returning to windowed mode.


## Update: Ctrl+S and repeat with the 3 key

- 17 tests passed: model and interface.
- Ctrl+S turns zoom selection on/off without triggering the S (stop) shortcut.
- Mouse drag in split full screen zooms each view separately,
  keeping full screen and the controls hidden.
- Key 3 sets A on the first press and B on the second; another press starts a new
  range. C clears A–B. Ranges shorter than 0.1 s are refused without losing A.
- The shortcuts were checked in windowed mode and in full screen, including with
  focus on the speed control. Key 3 with no video does not change the markers.
- The executable test also simulates Ctrl+S/drag in full screen and two presses
  of 3 while a synthetic video plays.

## Update: Ctrl+D

- Ctrl+D toggles one/two views in windowed mode and in full screen.
- Toggling keeps each view's zoom and does not leave full screen.
- 17 tests passed; the executable diagnostic checks the new shortcut.


## Update: bottom controls, Ctrl+Z, modes and recording

- 26 model/interface/PCM tests passed and 25 real playback checks.
- All buttons are in the bottom panel, with icons and shortcut hints.
- Repeating the video keeps the split and both crops; verified with real VLC.
- Ctrl+Z resets only the selected view, also in full screen.
- Sequential / random-video / shuffled-list order and repeat are independent.
- Real MP4 recording: two views with zoom, slow motion, pause, switch to full
  screen and a second recording. Pixels of the decoded MP4 were compared with the
  source composition, and the decoded audio had its RMS energy checked.
- Result: test-output/recording/results.json. Default recording folder: C:\Videos.
- The executable diagnostic records a synthetic video into the default folder and checks
  the shortcuts, the crops and that the file is finished with video and audio.

## Fix: open the video's location

- Selection uses SHParseDisplayName/SHOpenFolderAndSelectItems with the folder and
  the file passed separately, instead of text arguments to explorer.exe.
- The button uses the file being played even if the list position differs.
- A moved/renamed file and a Shell failure produce clear messages.
- COM initialization balanced through the Windows functions preserves the caller's
  state across repeated calls; a regression test is included.
- 32 model/interface/audio/Explorer tests passed.
- Real integration confirms the folder and the exact selection in four situations: accents,
  spaces, commas and symbols; commas without spaces; same names in different
  folders; reuse of the first folder. Source and executable results:
  test-output/explorer-cases/source-results.json and packaged-results.json.

## Fix: initial volume and video change

- The earlier failure was reproduced: PCM with the same energy at volume 100 and 10;
  volume requests made before the VLC output existed returned a failure.
- The slider controls QAudioSink directly. Its gain is applied before the output starts
  and after each re-initialization, without depending on VLC's asynchronous state.
- Volume restored on open, mute, file change, repeat and seek
  keep the chosen gain. VLC's volume callback does not change that state.
- Recording uses the original PCM with the playback gain history; volume/mute changes
  are applied at the right instant of the samples.
- 38 automated tests passed. A test with real VLC and Qt output confirmed
  a start at 7%, repeat/change at 7%, mute preserved, return to 3% and zero.
  The recording's PCM energy confirmed those gains; test-output/volume-results.json.
- MP4 recording integration passed, including audio, pause, slow motion,
  dual zoom, full screen and finishing on close.
- The executable diagnostic checks the initial output at 7% and mute toggling.
  Diagnostics do not overwrite the user's saved preferences.

## The - shortcut for slow motion

- Key - applies 0.75×, then 0.5× and 0.25×; further presses stay at 0.25×.
- Also works in full screen, with focus on volume/speed and on the numeric keypad.
- Auto-repeat while holding the key is disabled: one step per press.
- F1 help, speed hint and README updated.
- 39 automated tests passed. The executable diagnostic checks the real VLC speed,
  the limit, full screen and the numeric keypad.

## The + shortcut to recover and raise speed

- Key + raises in steps: 0.25×, 0.5×, 0.75×, 1×, 1.25×, 1.5× and 2×.
- From 2×, further presses stay at the limit. One step per press.
- Works in full screen, with focus on the controls, on the numeric keypad and with Shift
  to type the + sign on the main keyboard.
- F1 help, speed hint and README updated. 40 tests passed.
- The executable diagnostic checks recovery from slow motion, normal speed
  and speed-up to 2× with real VLC, including in full screen.

## Ctrl+R: independent rotation per view

- Ctrl+R rotates the selected view 90° clockwise: 0°, 90°, 180°, 270°, 0°.
- Icon in the bottom panel, image menu and F1 help included.
- Works in windowed/full screen; Ctrl+Z resets only the zoom, keeping the rotation.
- Aspect ratio preserved. Selections made on the rotated image are converted
  to the crop of the original image, including successive zooms.
- Repeat keeps the rotations of both views and the crops.
- Screen and recording share the same drawing function, without rotating/copying the
  decoded frame and without changing the synchronization between views.
- 43 tests passed. Coloured quadrants confirm the clockwise direction, all
  angles, aspect ratio, independence between views and the pixels of the recorded composition.
- A real MP4 with views at 90°/270°, zoom, slow motion, pause and full screen passed:
  decoded pixels compared with the composition, mean error 7.59/255.
  Results in test-output/recording/results.json.
- The executable diagnostic checks the full cycle and independent rotation in
  full screen and recording to C:\Videos.

## Real-time noise suppression

- On/off icon in the bottom panel, Soft/Medium/Strong levels, Ctrl+H and the
  full-screen image menu. The on/strength preference was persisted.
- Adaptive stereo spectral filter on overlapping windows of 1024 samples,
  vectorized FFT and a gain shared between channels. The 512-sample look-ahead is
  compensated with the original timestamps; duration and alignment preserved.
- Original/filtered audio kept in bounded buffers. Strength changes
  follow the playback and recording instant. Seek/repeat resets the
  estimator and discards future audio, keeping samples already used in the recording.
- 52 tests passed: progressive reduction, preservation of the main signal,
  exact duration with irregular blocks, stereo, silence, finishing, seek,
  transitions between levels, full screen and restoring preferences.
- Real VLC: noise RMS ratio 0.728/0.480/0.174 at soft/medium/strong.
  A 1 kHz signal kept 94.9% of its RMS energy in a noise + signal scenario.
  A recorded and decoded AAC MP4 confirmed the noise reduction. Seek, slow motion
  and turning the filter off were checked; test-output/noise/results.json.
- Recording with strong suppression, dual zoom, 90°/270° rotations, slow motion,
  pause and full screen passed; test-output/recording/results.json.
- The executable diagnostic checks Ctrl+H in full screen, that filtered data is
  used in the recording, and the NumPy distribution inside the app.


## Adjustable suppression from 0 to 100% — 2026-10-06

- Bar in the bottom tab with a visible percentage and 1% steps.
- The same bar is available in the right-click menu in full screen.
- 0% keeps the original PCM; 100% uses the full filter. Intermediate values
  mix the original audio with the filtered audio, without changing the main volume.
- Playback and recording use the same strength at every instant.
- Percentage saved on close; old levels migrated to 35%, 65% and 100%.
- 54 tests passed, including all 101 values and changes in the middle of the PCM.
- Integration with VLC and MP4/AAC passed at 35%, 65% and 100%, including slow motion,
  seek and the return to the original audio when turned off.


## Preferences and dragged videos — 2026-10-16

- Sequential/random video/shuffle list order and repeat off/video/list
  are restored with their icons; split screen, volume and mute too.
- The suppressor starts off on every launch, including after closing with it
  on. The chosen percentage is still saved.
- Dragging videos immediately plays the first valid one, including videos already
  in the list and drags while another file is playing.
- 57 tests passed: order and repeat combinations, invalid modes, volume,
  split screen, suppressor off and dragging several videos without duplicates.
- tests/preferences_integration.py passed with QSettings in a real INI file,
  reopening the window and Qt drag events alternating MP4 and HEVC through VLC.
  Result: test-output/preferences-drop/results.json.


## Interface languages — 2026-10-21 (English and Brazilian Portuguese)

What changed: every user-facing string moved into `duplo/i18n.py` as English / Portuguese pairs
(window, buttons, tooltips, status bar, dialogs, context menu, F1 help, welcome screen, error
messages). Enum names shown to the user (`Repeat`, `PlaybackOrder`) now come from `.label`;
their `.value` is a stable identifier. The saved preferences use enum names and are not affected.

What was checked, outside Windows, with a stubbed VLC engine:

- `tests/test_i18n.py` (11 new tests) passed: both languages present for every key with the same
  placeholders; no Portuguese accents in any English text; same number of lines in the F1 help;
  `DUPLO_LANG` / saved setting / fallback order; enum labels follow the language; an English window shows no
  Portuguese text in labels, tooltips and accessible names; choosing a language saves it once.
- A static check confirmed that every `tr(...)` call uses an existing key with the right placeholders.

Run on Windows 11 Pro (10.0.26200), Python 3.11, VLC 3.0.24 — 2026-10-21:

- `i18n.system_language()` returned `pt` on this machine.
- `python -m unittest discover -s tests -v`: 68 tests, 0 failures, 0 errors (27 in `test_ui.py`, 11 in `test_i18n.py`).
- Integration scripts with the real VLC engine, run one at a time: `noise_integration.py`, `volume_integration.py`,
  `preferences_integration.py` and `explorer_integration.py` passed. Their fixture videos were created with
  `make_fixture` from `integration.py`, without running that script's `main()`.
- `integration.py` (it sends a disposable copy to the real Windows Recycle Bin): the first run stopped at the
  A–B loop check with 1 return to point A instead of at least 2, after 16 checks; the next run, unchanged,
  passed all 25 checks (3 returns to A), including the dialog buttons clicked through `tr(...)`. Two more runs,
  unchanged, both stopped at the same A–B check (1 return to A, after 16 checks): 1 of these 3 runs passed all
  25 checks (4 runs in total: 1 passed, 3 stopped at the A–B check). The test was not changed.
- Cause of the A–B failures, found by tracing the unchanged test: the check runs on the last format fixture,
  `teste_av1.mkv` (2 s), and B often landed about 80 ms before the end of the file. VLC reports the time in
  steps of about 250–300 ms, so the file ended before a time ≥ B was reported. The app's end-of-file path
  then reloaded the file and called `_restore_position(A)`, but the seek was sent while the new media was
  still opening; VLC ignored it and playback restarted from 0 instead of A.
- Fix in `duplo/window.py`: `_restore_position` now waits until the player is `Playing` (and seekable)
  before seeking, retrying every 100 ms as before. This also covers the position restore after a Recycle
  Bin failure. After the fix: 68 unit tests passed; `integration.py` passed all 25 checks in 4 of 4 runs
  (3, 2, 2 and 2 returns to A; the test asks for at least 2); `recording_integration.py`,
  `volume_integration.py`, `noise_integration.py`, `preferences_integration.py` and
  `explorer_integration.py` passed.
- `recording_integration.py` passed (records into `test-output\recording`, not `C:\Videos`): composed MP4
  1268×644, 3.53 s, noise suppression 100, dual zoom, rotations 90/270, slow motion, pause, full screen,
  second recording and finalizing on close.
- Offscreen window captured in English and in Portuguese: no text cut off or overlapping, and no Portuguese
  in the English window.
- Real app (`main.py`) opened with a synthetic video: with `DUPLO_LANG=en` and `DUPLO_LANG=pt`, the labels,
  status bar, F1 help and right-click menu appeared in the chosen language. Choosing a language from
  "Idioma / Language" saved `language` in a temporary INI `QSettings`; without `DUPLO_LANG`, the next start
  used the saved value (`en`, then `pt`).
- `build.ps1` produced `dist\DuploPlayer\DuploPlayer.exe` with the eight documents. `installer.ps1` produced
  the installer; a silent install (`/VERYSILENT`) into a temporary folder finished without a language
  dialog, the installed app passed `--smoke-test` with `DUPLO_LANG=en` (VLC 3.0.24, 76 recorded frames,
  noise suppression 100), and the silent uninstall removed the files and the Start menu shortcut.

## Floating timeline in full screen and joined recording segments — 22/10/2026

- Full screen now shows a floating timeline (seek bar and time) over the bottom of the video while the mouse
  is within 90 px of the bottom edge or dragging it; it hides when the mouse leaves. It is a child of the
  window, not of the views, so it is never drawn into recordings.
- Ctrl+G still records one MP4 per start/stop. Ctrl+Shift+G (button and right-click menu) joins the segments
  recorded since the last join, in order, with an FFmpeg stream copy (no re-encoding). Later segments reuse
  the first segment's frame size. After the join, and once the joined file's duration matches the segments,
  the segments are deleted permanently (not via the Recycle Bin); on failure they are kept.
- 71 unit tests passed (3 new: timeline shows/hides by cursor zone and leaves with full screen; a click on it
  seeks; joining needs two segments). `integration.py` passed all 25 checks; `recording_integration.py` passed.
- New `segments_integration.py` passed with the real VLC and FFmpeg (into `test-output\segments`): 3 segments of 1.03, 1.23 and 0.83 s recorded in window, full screen and split
  view, all 1268×644, joined into one 3.12 s MP4 with AAC audio that decodes without errors; Ctrl+Shift+G
  while recording finished that segment and joined 2 segments; the joined segment files were deleted, and a
  joined file shorter than its segments (simulated) was discarded with the segments kept.
