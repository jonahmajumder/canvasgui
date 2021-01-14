import sys
from pathlib import Path
from datetime import datetime

IS_BUNDLED = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

LOGFILE = 'log.txt'

def log_header():
    header = ''
    header += 'Log file initiated at {}.\n'.format(datetime.now().isoformat())
    header += 50 * '-'
    header += '\n\n'
    return header

if IS_BUNDLED:
    RELATIVE_PATH = Path(sys._MEIPASS).parent / 'Resources'
else:
    RELATIVE_PATH = Path(__file__).parents[1]

# in Resource dir within app bundle
def ResourceFile(path):
    return str(Path.cwd() / RELATIVE_PATH / path)

HOME = Path.home()

DOWNLOADS = HOME / 'Downloads'

DOCUMENTS = HOME / 'Documents'

if IS_BUNDLED:
    # set up app to write to logfile
    with open(ResourceFile(LOGFILE), 'w') as file:
        file.write(log_header())
    sys.stdout = open(ResourceFile(LOGFILE), 'a')
    sys.stderr = open(ResourceFile(LOGFILE), 'a')