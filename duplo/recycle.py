"""Recycle a single local file. Abort any permanent-delete operation.

Use the modern Windows API directly, with a progress sink that vetoes an
operation when Windows does not advertise recycling. Never use unlink or
SHFileOperation's legacy fallback.
"""
import ctypes
from pathlib import Path
import sys

from .i18n import tr


def recycle(path):
    if sys.platform != 'win32':
        raise OSError(tr('recycle.windows_only'))
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise OSError(tr('recycle.bad_target'))
    path = path.resolve()
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetDriveTypeW.argtypes = [ctypes.c_wchar_p]
    kernel.GetDriveTypeW.restype = ctypes.c_uint
    if kernel.GetDriveTypeW(path.anchor) != 3:  # DRIVE_FIXED
        raise OSError(tr('recycle.fixed_only'))

    import pythoncom
    import pywintypes
    from win32com.server.exception import COMException
    from win32com.shell import shell, shellcon
    from send2trash.win.IFileOperationProgressSink import FileOperationProgressSink

    class RecycleOnlySink(FileOperationProgressSink):
        def __init__(self):
            super().__init__()
            self.recycled = False
            self.failed = None

        def PreDeleteItem(self, flags, item):
            if not flags & shellcon.TSF_DELETE_RECYCLE_IF_POSSIBLE:
                self.failed = tr('recycle.unavailable')
                raise COMException(desc=self.failed, scode=pythoncom.E_FAIL)

        def PostDeleteItem(self, flags, item, result, newly_created):
            if result < 0:
                self.failed = f'Falha do Windows ao reciclar: {result:#x}'
            elif newly_created is not None:
                self.recycled = True

    pythoncom.CoInitialize()
    operation = item = sink = None
    try:
        operation = pythoncom.CoCreateInstance(shell.CLSID_FileOperation, None,
                                               pythoncom.CLSCTX_INPROC_SERVER,
                                               shell.IID_IFileOperation)
        # FOFX_RECYCLEONDELETE, FOFX_ADDUNDORECORD, FOFX_EARLYFAILURE.
        flags = (shellcon.FOF_SILENT | shellcon.FOF_NOCONFIRMATION |
                 shellcon.FOF_NOERRORUI | 0x00080000 | 0x20000000 | 0x00100000)
        operation.SetOperationFlags(flags)
        implementation = RecycleOnlySink()
        sink = pythoncom.WrapObject(implementation, shell.IID_IFileOperationProgressSink)
        item = shell.SHCreateItemFromParsingName(str(path), None, shell.IID_IShellItem)
        operation.DeleteItem(item, sink)
        result = operation.PerformOperations()
        if result or operation.GetAnyOperationsAborted() or implementation.failed:
            raise OSError(implementation.failed or tr('recycle.cancelled'))
        if not implementation.recycled or path.exists():
            raise OSError(tr('recycle.unconfirmed'))
    except pywintypes.com_error as exc:
        raise OSError(exc.strerror) from exc
    finally:
        operation = item = sink = None
        pythoncom.CoUninitialize()
