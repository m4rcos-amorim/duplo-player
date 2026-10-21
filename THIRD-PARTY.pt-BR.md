# Componentes de terceiros

- VLC 3.0.24 / LibVLC: VideoLAN, distribuição portátil oficial.
  https://www.videolan.org/vlc/ — https://www.videolan.org/legal.html
  Os arquivos de licença e avisos originais estão em `vendor/vlc`.
- Qt / PySide6 6.11.2: The Qt Company e colaboradores, LGPL/GPL/comercial.
  https://doc.qt.io/qtforpython-6/licenses.html
  As bibliotecas são distribuídas separadamente no pacote e podem ser substituídas.
- python-vlc 3.0.21203: LGPL 2.1 ou posterior.
  https://github.com/oaubert/python-vlc
- Send2Trash 2.1.0: licença BSD.
  https://github.com/arsenetar/send2trash
- pywin32 312: licença PSF.
  https://github.com/mhammond/pywin32
- PyInstaller: GPL com exceção para distribuição do aplicativo gerado.
  https://pyinstaller.org/en/stable/license.html

- imageio-ffmpeg 0.6.0: BSD-2-Clause. Empacota o executável FFmpeg usado na gravação.
  https://github.com/imageio/imageio-ffmpeg
- FFmpeg 7.1 essentials, Gyan.dev: executável separado, GPLv3, incluindo libx264.
  https://ffmpeg.org/legal.html — https://www.gyan.dev/ffmpeg/builds/
  Licença em licenses/FFmpeg-GPLv3.txt; fontes FFmpeg correspondentes:
  https://ffmpeg.org/releases/ffmpeg-7.1.tar.xz
  Fontes e configuração dos builds: https://github.com/GyanD/codexffmpeg

O código do aplicativo está incluído na pasta do projeto. O executável FFmpeg
fica separado em _internal/imageio_ffmpeg/binaries e é usado como subprocesso
para codificar gravações. VLC continua responsável por decodificar os vídeos.
PyInstaller é uma dependência de desenvolvimento para empacotamento.

Referências de implementação:
- Callbacks de LibVLC: https://videolan.videolan.me/vlc-3.0/group__libvlc__media__player.html
- Recorte de imagem no Qt: https://doc.qt.io/qtforpython-6/PySide6/QtGui/QPainter.html
- Lixeira: https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-ifileoperation-setoperationflags
- Veto de exclusão: https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-ifileoperationprogresssink-predeleteitem

- NumPy 2.4.6: BSD-3-Clause e componentes com avisos próprios. FFT e operações
  vetoriais usadas na redução espectral de ruído. Licenças distribuídas em
  licenses/NumPy, incluindo PocketFFT e bibliotecas do wheel oficial.
  https://numpy.org/ — https://github.com/numpy/numpy/tree/v2.4.6
  O filtro em duplo/noise.py é implementado pelo projeto; não utiliza RNNoise.
