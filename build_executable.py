#!/usr/bin/env python3
"""
Script to build executable using PyInstaller
"""

import os
import sys
import shutil
from pathlib import Path

def build_executable():
    """Build Windows executable"""
    print("Building Visitor Management System executable...")
    
    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name=VisitorManagementSystem",
        "--icon=icon.ico",  # Add icon if available
        "--add-data=requirements.txt;.",
        "--hidden-import=PyQt5.sip",
        "--hidden-import=pandas",
        "--hidden-import=matplotlib",
        "--hidden-import=openpyxl",
        "--hidden-import=psutil",
        "--hidden-import=cryptography",
        "main.py"
    ]
    
    # Run PyInstaller
    import subprocess
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("Build successful!")
        print("Executable created in 'dist' directory")
        
        # Create distribution package
        dist_dir = Path("dist")
        if dist_dir.exists():
            print("\nCreating distribution package...")
            
            # Copy additional files
            files_to_copy = [
                "README.md",
                "requirements.txt"
            ]
            
            for file in files_to_copy:
                if Path(file).exists():
                    shutil.copy2(file, dist_dir)
            
            print("Distribution package ready!")
    else:
        print("Build failed!")
        print("Error:", result.stderr)
        return False
    
    return True

if __name__ == "__main__":
    if not build_executable():
        sys.exit(1)