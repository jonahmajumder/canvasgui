import sys
from pathlib import Path

IS_BUNDLED = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

if IS_BUNDLED:
    RELATIVE_PATH = Path(sys._MEIPASS).parent / 'Resources'
else:
    RELATIVE_PATH = Path(__file__).parent

# in Resource dir within app bundle
def ResourceFile(path):
    return str(Path.cwd() / RELATIVE_PATH / path)

HOME = Path.home()

DOWNLOADS = HOME / 'Downloads'

DOCUMENTS = HOME / 'Documents'