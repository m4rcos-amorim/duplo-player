from pathlib import Path
import tempfile
import unittest
from unittest.mock import call, patch
from duplo.explorer import reveal_in_explorer


class ExplorerTests(unittest.TestCase):
    def test_missing_file_never_calls_windows(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'missing.mp4'
            with patch('win32com.shell.shell.SHParseDisplayName') as parse:
                with self.assertRaises(FileNotFoundError):
                    reveal_in_explorer(path)
                parse.assert_not_called()

    def test_windows_identity_is_used_for_special_characters(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'ação, espaços & [parênteses] #1.mp4'
            path.write_bytes(b'disposable fixture')
            folder_pidl = [b'Windows-owned folder identity']
            file_pidl = folder_pidl + [b'Windows-owned file identity']
            with patch('win32com.shell.shell.SHParseDisplayName', side_effect=[(folder_pidl, 0), (file_pidl, 0)]) as parse, \
                 patch('win32com.shell.shell.SHOpenFolderAndSelectItems') as select:
                reveal_in_explorer(path)
                self.assertEqual(parse.call_args_list, [call(str(path.resolve().parent), 0), call(str(path.resolve()), 0)])
                select.assert_called_once_with(folder_pidl, [file_pidl[-1:]], 0)

    def test_native_selection_failure_is_reported(self):
        import pywintypes
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'video.mp4'
            path.write_bytes(b'disposable fixture')
            with patch('win32com.shell.shell.SHParseDisplayName', return_value=([b'item'], 0)), \
                 patch('win32com.shell.shell.SHOpenFolderAndSelectItems',
                       side_effect=pywintypes.com_error(-2147467259, 'Simulated failure', None, None)):
                with self.assertRaisesRegex(OSError, 'Simulated failure'):
                    reveal_in_explorer(path)

    def test_preserves_callers_initialized_com_apartment(self):
        import ctypes
        import pythoncom
        pythoncom.CoInitialize()
        ole32 = ctypes.WinDLL('ole32')
        apartment, qualifier = ctypes.c_int(), ctypes.c_int()
        self.assertEqual(ole32.CoGetApartmentType(ctypes.byref(apartment), ctypes.byref(qualifier)), 0)
        before = (apartment.value, qualifier.value)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'video.mp4'
            path.write_bytes(b'disposable fixture')
            with patch('win32com.shell.shell.SHParseDisplayName', return_value=([b'item'], 0)), \
                 patch('win32com.shell.shell.SHOpenFolderAndSelectItems'):
                reveal_in_explorer(path)
                reveal_in_explorer(path)
        self.assertEqual(ole32.CoGetApartmentType(ctypes.byref(apartment), ctypes.byref(qualifier)), 0)
        self.assertEqual((apartment.value, qualifier.value), before)
