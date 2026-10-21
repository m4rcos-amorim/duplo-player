# Third-party components

Portuguese version: `THIRD-PARTY.pt-BR.md`.

- VLC 3.0.24 / LibVLC: VideoLAN, official portable distribution.
  https://www.videolan.org/vlc/ — https://www.videolan.org/legal.html
  The original license files and notices are in `vendor/vlc`.
- Qt / PySide6 6.11.2: The Qt Company and contributors, LGPL/GPL/commercial.
  https://doc.qt.io/qtforpython-6/licenses.html
  The libraries ship separately inside the package and can be replaced.
- python-vlc 3.0.21203: LGPL 2.1 or later.
  https://github.com/oaubert/python-vlc
- Send2Trash 2.1.0: BSD license.
  https://github.com/arsenetar/send2trash
- pywin32 312: PSF license.
  https://github.com/mhammond/pywin32
- PyInstaller: GPL with an exception that allows distributing the generated application.
  https://pyinstaller.org/en/stable/license.html

- imageio-ffmpeg 0.6.0: BSD-2-Clause. Packages the FFmpeg executable used for recording.
  https://github.com/imageio/imageio-ffmpeg
- FFmpeg 7.1 essentials, Gyan.dev: separate executable, GPLv3, including libx264.
  https://ffmpeg.org/legal.html — https://www.gyan.dev/ffmpeg/builds/
  License in licenses/FFmpeg-GPLv3.txt; corresponding FFmpeg sources:
  https://ffmpeg.org/releases/ffmpeg-7.1.tar.xz
  Sources and build configuration: https://github.com/GyanD/codexffmpeg

The application code is included in the project folder. The FFmpeg executable
stays separate in _internal/imageio_ffmpeg/binaries and is used as a subprocess
to encode recordings. VLC remains responsible for decoding the videos.
PyInstaller is a development dependency used for packaging.

Implementation references:
- LibVLC callbacks: https://videolan.videolan.me/vlc-3.0/group__libvlc__media__player.html
- Image cropping in Qt: https://doc.qt.io/qtforpython-6/PySide6/QtGui/QPainter.html
- Recycle Bin: https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-ifileoperation-setoperationflags
- Delete veto: https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-ifileoperationprogresssink-predeleteitem

- NumPy 2.4.6: BSD-3-Clause, and components with their own notices. FFT and vectorized
  operations used in the spectral noise reduction. Licenses are shipped in
  licenses/NumPy, including PocketFFT and the libraries in the official wheel.
  https://numpy.org/ — https://github.com/numpy/numpy/tree/v2.4.6
  The filter in duplo/noise.py is implemented by this project; it does not use RNNoise.
