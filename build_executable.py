#!/usr/bin/env python3
"""
Correct build script for M-Neo VMS
Produces a folder-based PyInstaller build compatible with installer.iss
"""

import os
import subprocess
import shutil
from pathlib import Path

APP_NAME = "M-Neo VMS"
DIST_DIR = Path("dist") / APP_NAME

def clean_previous_build():
    print("Cleaning previous build...")
    shutil.rmtree("build", ignore_errors=True)
    shutil.rmtree("dist", ignore_errors=True)
    shutil.rmtree("__pycache__", ignore_errors=True)

def build_executable():
    print("Building application with PyInstaller...")

    # Folder-based build (NO --onefile)
    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--windowed",
        f"--name={APP_NAME}",
        "--add-data=assets;assets",
        "--add-data=data;data",
        "--add-data=ui;ui",
        "--add-data=utils;utils",
        "--add-data=passes;passes",
        "--hidden-import=PyQt5.sip",
        "--hidden-import=pandas",
        "--hidden-import=matplotlib",
        "--hidden-import=openpyxl",
        "--hidden-import=psutil",
        "--hidden-import=cryptography",
        "main.py"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("❌ Build failed:")
        print(result.stderr)
        return False

    print("✅ Build succeeded!")
    print(f"Output created at: dist/{APP_NAME}")
    return True

if __name__ == "__main__":
    clean_previous_build()
    ok = build_executable()
    if not ok:
        exit(1)
