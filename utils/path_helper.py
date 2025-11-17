import sys, os

def resource_path(relative_path):
    """ Get correct absolute path for PyInstaller and normal run """
    if hasattr(sys, '_MEIPASS'):  # Running inside EXE
        base_path = sys._MEIPASS
    else:  # Running from script
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
