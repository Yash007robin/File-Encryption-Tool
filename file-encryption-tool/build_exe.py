"""
Build script — packages the app into a standalone executable using PyInstaller.
Run this from inside your activated venv after installing pyinstaller:

    pip install pyinstaller
    python build_exe.py

Output goes to dist/FileEncryptionTool(.exe on Windows).
Users who receive the built executable do NOT need Python installed.
"""

import PyInstaller.__main__
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PyInstaller.__main__.run([
    "app.py",
    "--name=FileEncryptionTool",
    "--onefile",
    "--add-data=templates{}templates".format(os.pathsep),
    "--add-data=static{}static".format(os.pathsep),
    "--noconsole",  # hide the terminal window on Windows; remove this line if you want console output for debugging
    "--clean",
])

print("\nBuild complete. Find the executable in the dist/ folder.")
print("Share dist/FileEncryptionTool(.exe) — recipients need no Python install.")