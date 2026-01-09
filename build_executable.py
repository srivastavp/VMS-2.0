#!/usr/bin/env python3
"""
Build script for M-Neo VMS
Produces a folder-based PyInstaller build for Inno Setup
"""
import subprocess
import shutil
import sys
from pathlib import Path

APP_NAME = "M-Neo VMS"
PROJECT_ROOT = Path(__file__).resolve().parent
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"

def clean_previous_build():
    print("🧹 Cleaning previous build...")
    shutil.rmtree(BUILD_DIR, ignore_errors=True)
    shutil.rmtree(DIST_DIR, ignore_errors=True)
    shutil.rmtree(PROJECT_ROOT / "__pycache__", ignore_errors=True)

def build_executable():
    print("⚙️ Building application with PyInstaller...")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--windowed",
        "--name", APP_NAME,

        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR),
        "--specpath", str(PROJECT_ROOT),

        # Static assets only
        "--add-data", "assets;assets",

        # Hidden imports
        "--hidden-import", "PyQt5.sip",
        "--hidden-import", "pandas",
        "--hidden-import", "matplotlib",
        "--hidden-import", "openpyxl",
        "--hidden-import", "psutil",
        "--hidden-import", "cryptography",
        "--hidden-import", "qrcode",
        "--hidden-import", "reportlab",
        "--hidden-import", "PIL",

        "main.py",
    ]

    result = subprocess.run(cmd, text=True, cwd=str(PROJECT_ROOT))

    if result.returncode != 0:
        raise RuntimeError(f"❌ PyInstaller build failed (exit code {result.returncode})")

    print("✅ Build succeeded!")
    print(f"📦 Output available at: {DIST_DIR / APP_NAME}")

def verify_output():
    exe = DIST_DIR / APP_NAME / f"{APP_NAME}.exe"
    if not exe.exists():
        raise RuntimeError("❌ Build verification failed: exe not found")

if __name__ == "__main__":
    clean_previous_build()
    build_executable()
    verify_output()
