import sys
from time import time

from PyQt5.Qt import QApplication

from classdefs import CONTENT_TYPES

from app import CanvasApp

app = QApplication(sys.argv)

start = time()

gui = CanvasApp()

loadtime = time() - start

print('Load time: {:.2f} s'.format(loadtime))

courseitems = len(CONTENT_TYPES) * len(list(gui.canvas.get_courses(include=['term', 'favorites'])))

while gui.model.rowCount() < courseitems:
    pass

print('All {} items loaded.'.format(gui.model.rowCount()))

start = time()

toplevel = [gui.model.invisibleRootItem().child(i, 0) for i in range(gui.model.rowCount())]

include = range(0, len(toplevel))

for i, item in enumerate(toplevel):
    if i in include:
        try:
            print('Expanding item {0}: {1}.'.format(i, item))
            item.expand_recursive()
        except Exception as e:
            raise e

expandtime = time() - start

print('Expand time: {:.2f} s'.format(expandtime))
