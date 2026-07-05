import os
import sys

try:
    import ctypes
    wh = ctypes.windll.kernel32.GetConsoleWindow()
    if wh:
        ctypes.windll.user32.ShowWindow(wh, 0)
except:
    pass

from app import app, DB_PATH
from init_db import init_db

if __name__ == '__main__':
    init_db()
    from flaskwebgui import FlaskUI
    FlaskUI(
        server=app.run,
        server_kwargs={'host': '127.0.0.1', 'port': 5001, 'debug': False, 'use_reloader': False},
        port=5001,
        width=1280,
        height=800,
        fullscreen=False
    ).run()