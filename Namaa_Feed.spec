# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('templates', 'templates'), ('static', 'static')]
binaries = []
hiddenimports = ['flask', 'sqlite3', 'hashlib', 'flaskwebgui']
tmp_ret = collect_all('flaskwebgui')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['C:\\Users\\bahaa.mohamed\\Desktop\\الانظمة\\نظام طلبات شركة قويسنا\\Namaa_Feed\\desktop_app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Namaa_Feed',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:\\Users\\bahaa.mohamed\\Desktop\\الانظمة\\نظام طلبات شركة قويسنا\\Namaa_Feed\\static\\icon.ico'],
)
