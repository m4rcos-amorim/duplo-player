"""Select a file by its native Shell identity, without Explorer CLI parsing."""
import ctypes
from pathlib import Path
import sys

from .i18n import tr


def reveal_in_explorer(path):
    if sys.platform != 'win32':
        raise OSError(tr('explorer.windows_only'))
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(tr('explorer.missing', path=path))
    path = path.resolve(strict=True)
    import pythoncom
    import pywintypes
    from win32com.shell import shell

    # Use the OS calls directly: pythoncom caches initialization on the main
    # thread, so nesting its Initialize/Uninitialize can tear down caller COM.
    ole32 = ctypes.WinDLL('ole32')
    ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    ole32.CoInitializeEx.restype = ctypes.c_long
    ole32.CoUninitialize.argtypes = []
    ole32.CoUninitialize.restype = None
    result = ole32.CoInitializeEx(None, pythoncom.COINIT_APARTMENTTHREADED)
    initialized = result >= 0
    if result < 0 and result != -2147417850:  # RPC_E_CHANGED_MODE
        raise OSError(tr('explorer.init_failed', code=result & 0xffffffff))
    try:
        folder_pidl, _ = shell.SHParseDisplayName(str(path.parent), 0)
        file_pidl, _ = shell.SHParseDisplayName(str(path), 0)
        # Pass the folder separately and the final item relative to it. This
        # explicitly selects the video when Explorer reuses an existing window.
        shell.SHOpenFolderAndSelectItems(folder_pidl, [file_pidl[-1:]], 0)
    except pywintypes.com_error as exc:
        raise OSError(tr('explorer.open_failed', detail=exc.strerror or str(exc))) from exc
    finally:
        if initialized:
            ole32.CoUninitialize()
