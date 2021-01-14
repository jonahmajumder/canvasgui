# when app is bundled, this makes sure that all output is captured
# by redirected stdout/stderr file
from locations import *

import sys

from PyQt5.Qt import QApplication

from app import CanvasApp

app = QApplication(sys.argv)
gui = CanvasApp()

if __name__ == '__main__':
    sys.exit(app.exec_()) # block until qapp instance exits