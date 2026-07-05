import os
import sys
import subprocess
import shutil
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

base_dir = os.path.dirname(__file__)
output_dir = os.path.join(base_dir, 'dist')
ico = os.path.join(base_dir, 'static', 'icon.ico')

for d in ['build', 'dist', '__pycache__']:
    p = os.path.join(base_dir, d)
    if os.path.exists(p):
        shutil.rmtree(p, ignore_errors=True)
for f in ['Namaa_Feed.spec']:
    p = os.path.join(base_dir, f)
    if os.path.exists(p):
        os.remove(p)

cmd = [
    sys.executable, '-m', 'PyInstaller',
    '--onefile',
    '--windowed',
    '--name', 'Namaa_Feed',
    '--add-data', f'templates{os.pathsep}templates',
    '--add-data', f'static{os.pathsep}static',
    '--add-data', f'init_db.py{os.pathsep}.',
    '--add-data', f'export_utils.py{os.pathsep}.',
    '--collect-all', 'flaskwebgui',
    '--hidden-import', 'flask',
    '--hidden-import', 'sqlite3',
    '--hidden-import', 'hashlib',
    '--hidden-import', 'flaskwebgui',
    '--hidden-import', 'openpyxl',
    '--icon', ico,
    '--distpath', output_dir,
    '--noconfirm',
    os.path.join(base_dir, 'desktop_app.py')
]

result = subprocess.run(cmd, capture_output=True, text=True)
sys.stdout.write(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
if result.returncode != 0:
    sys.stdout.write(result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr)
else:
    exe_path = os.path.join(output_dir, 'Namaa_Feed.exe')
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / 1024 / 1024
        print(f'\nDone! File size: {size_mb:.1f} MB')
        print(f'Path: {output_dir}')
    else:
        print('\nBuild failed - exe not found')
