import argparse
from pathlib import Path
import sys
import traceback

from duplo import i18n
from duplo.i18n import tr

try:
    from PySide6.QtCore import QSettings
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication, QMessageBox
except ImportError:
    # Capture loader diagnostics even if Qt fails before a window can exist.
    import ctypes
    loader = ctypes.WinDLL('kernel32')
    loader.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
    loader.GetModuleHandleW.restype = ctypes.c_void_p
    loader.GetModuleFileNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint]
    libraries = []
    for name in ['Qt6Core.dll', 'Qt6Gui.dll', 'pyside6.abi3.dll', 'shiboken6.abi3.dll',
                 'msvcp140.dll', 'vcruntime140.dll', 'vcruntime140_1.dll', 'python3.dll']:
        handle = loader.GetModuleHandleW(name)
        buffer = ctypes.create_unicode_buffer(32768)
        if handle:
            loader.GetModuleFileNameW(handle, buffer, len(buffer))
        libraries.append(f'{name}: {buffer.value}')
    destination = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent
    (destination / 'duplo-loader-error.log').write_text(traceback.format_exc() + '\n'.join(libraries), encoding='utf-8')
    raise


def main():
    parser = argparse.ArgumentParser(description='Duplo Player')
    parser.add_argument('files', nargs='*')
    parser.add_argument('--reveal-test', metavar='VIDEO', help=argparse.SUPPRESS)
    parser.add_argument('--smoke-test', metavar='VIDEO', help=argparse.SUPPRESS)
    parser.add_argument('--smoke-output', metavar='PASTA', help=argparse.SUPPRESS)
    args = parser.parse_args()
    app = QApplication(sys.argv)
    app.setApplicationName('Duplo Player')
    app.setOrganizationName('DuploPlayer')
    # DUPLO_LANG, then the saved choice, then the system language.
    i18n.init(None if args.smoke_test or args.reveal_test else QSettings('DuploPlayer', 'DuploPlayer'))
    if args.reveal_test:
        # Targeted frozen-build diagnostic; no playback or recording side effects.
        import json
        from duplo.explorer import reveal_in_explorer
        output = Path(args.smoke_output) if args.smoke_output else Path(sys.executable).parent
        output.mkdir(parents=True, exist_ok=True)
        report = {'result': 'PASS', 'file': str(Path(args.reveal_test).resolve())}
        try:
            reveal_in_explorer(args.reveal_test)
        except Exception as exc:
            report.update(result='FAIL', error=str(exc))
        (output / 'native-reveal.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        return 0 if report['result'] == 'PASS' else 1
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    app.setWindowIcon(QIcon(str(root / 'assets' / 'duplo.svg')))
    try:
        from duplo.window import PlayerWindow
        window = PlayerWindow(settings=not bool(args.smoke_test))
    except Exception as exc:
        QMessageBox.critical(None, tr('start.failed_title'), tr('start.failed_body', error=exc))
        return 1
    window.show()
    if args.smoke_test:
        from duplo.diagnostics import run_packaged_smoke
        run_packaged_smoke(app, window, args.smoke_test, args.smoke_output)
    elif args.files:
        window.add_paths(args.files)
    return app.exec()


if __name__ == '__main__':
    try:
        exit_code = main()
    except Exception as exc:
        # A windowed executable has no stderr. Preserve unexpected startup
        # errors beside the executable so failures are diagnosable.
        destination = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent
        log_path = destination / 'duplo-error.log'
        log_path.write_text(traceback.format_exc(), encoding='utf-8')
        if '--smoke-test' not in sys.argv:
            QMessageBox.critical(None, tr('start.error_title'), tr('start.error_body', error=exc, log=log_path))
        exit_code = 1
    raise SystemExit(exit_code)
