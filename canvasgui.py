import sys
from time import time
import webbrowser

from PyQt5.Qt import *
from PyQt5.QtGui import *

from canvasapi import Canvas
from canvasapi.exceptions import Unauthorized

from apistuff import *
from classdefs import *
from secrets import BASEURL, TOKEN

canvas = Canvas(BASEURL, TOKEN)

app = QApplication(sys.argv)
app.setAttribute(Qt.AA_UseHighDpiPixmaps)

main = QMainWindow()

tree = QTreeWidget()
tree.setHeaderLabels(['Course', 'Date Created'])
tree.setAlternatingRowColors(True)
tree.setColumnCount(2)
tree.header().setSectionResizeMode(QHeaderView.Stretch)

moduleSlider = SliderHLayout('Filesystem', 'Modules', startVal=True)

favoriteSlider = SliderHLayout('All Courses', 'Favorites', startVal=True)

expandButton = QPushButton('Expand All')

expandLayout = QHBoxLayout()
expandLayout.addItem(QSpacerItem(20,40))
expandLayout.addWidget(expandButton)
expandLayout.addItem(QSpacerItem(20,40))
expandLayout.setStretch(0, 1)
expandLayout.setStretch(1, 1)
expandLayout.setStretch(2, 1)

mainLayout = QVBoxLayout()

controlLayout = QHBoxLayout()
controlLayout.addLayout(moduleSlider)
controlLayout.addLayout(favoriteSlider)
controlLayout.addLayout(expandLayout)
controlLayout.setStretch(0, 1)
controlLayout.setStretch(1, 1)
controlLayout.setStretch(2, 1)

mainLayout.addLayout(controlLayout)
mainLayout.addWidget(tree)

central = QWidget()
central.setLayout(mainLayout)
main.setCentralWidget(central)

def add_courses(onlyFavorites, asModules):
    favorites, others = get_courses_separated(canvas)

    for course in favorites:
        CourseItem(tree, object=course, modules=asModules)

    if not onlyFavorites:
        SeparatorItem(tree)
        for course in others:
            CourseItem(tree, object=course, modules=asModules)
    
def moduleSliderChanged(asModules):
    onlyFavorites = favoriteSlider.value()
    tree.clear()
    add_courses(onlyFavorites, asModules)

def favoriteSliderChanged(onlyFavorites):
    asModules = moduleSlider.value()
    tree.clear()
    add_courses(onlyFavorites, asModules)

def expand_children(item):
    for i in range(item.childCount()):
        ch = item.child(i)
        if hasattr(ch, 'expand'):
            ch.dblClickFcn(advance=False)
        expand_children(ch)

def expand_all():
    start_time = time()
    expand_children(tree.invisibleRootItem())
    print('Load time: {:.2f}'.format(time() - start_time))

add_courses(favoriteSlider.value(), moduleSlider.value())

tree.itemDoubleClicked.connect(lambda item: item.dblClickFcn())

expandButton.clicked.connect(expand_all)
moduleSlider.valueChanged.connect(moduleSliderChanged)
favoriteSlider.valueChanged.connect(favoriteSliderChanged)

app.topLevelWidgets()[0].setGeometry(
    QStyle.alignedRect(
        Qt.LeftToRight,
        Qt.AlignCenter,
        QSize(800,600),
        tree.screen().geometry())
)

main.show()

if __name__ == '__main__':
    sys.exit(app.exec_())