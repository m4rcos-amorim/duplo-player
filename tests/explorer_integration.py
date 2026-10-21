"""Validate the actual folder AND selected file, using Shell API/packaged app.

Reads selection only in synthetic fixture folders. Never deletes source files
or closes unrelated Explorer windows.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import pythoncom
import win32com.client
from duplo.explorer import reveal_in_explorer

parser=argparse.ArgumentParser()
parser.add_argument('--exe', type=Path)
args=parser.parse_args()
output=ROOT / 'test-output' / 'explorer-cases'
fixtures=[]
for folder, name in [('nomes, com espaços & acentuação (á)', 'vídeo, teste & [01] #1.mp4'),
                     ('vírgulas,sem-espaço', 'vídeo,02.mp4'),
                     ('outra pasta', 'vídeo, teste & [01] #1.mp4')]:
    file=output / folder / name
    file.parent.mkdir(parents=True,exist_ok=True)
    if not file.exists():
        shutil.copyfile(ROOT / 'test-output' / 'teste_principal.mp4',file)
    fixtures.append(file.resolve())
checks=[]
pythoncom.CoInitialize()
try:
    for file in fixtures + [fixtures[0]]:
        if args.exe:
            run=subprocess.run([str(args.exe), '--reveal-test', str(file), '--smoke-output', str(output)],
                timeout=25, creationflags=subprocess.CREATE_NO_WINDOW)
            assert run.returncode==0, (output/'native-reveal.json').read_text(encoding='utf-8')
        else:
            reveal_in_explorer(file)
        application=win32com.client.Dispatch('Shell.Application')
        selected=False
        end=time.monotonic()+8
        while time.monotonic()<end and not selected:
            for window in application.Windows():
                try:
                    document=window.Document
                    if Path(document.Folder.Self.Path).resolve() != file.parent:
                        continue
                    paths=[Path(item.Path).resolve() for item in document.SelectedItems()]
                    if paths==[file]:
                        selected=True
                        break
                except Exception:
                    continue
            if not selected:
                time.sleep(.1)
        assert selected, 'Explorer did not confirm the selection of the synthetic file: ' + str(file)
        checks.append({'folder':str(file.parent),'file':file.name,'selected_exact_file':True})
        print('PASS: folder and selection verified:',file.parent.name,'/',file.name,flush=True)
finally:
    pythoncom.CoUninitialize()
report={'result':'PASS','mode':'packaged' if args.exe else 'source','checks':checks}
(output / ('packaged-results.json' if args.exe else 'source-results.json')).write_text(
    json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
