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

CONTENT_TYPES = ['modules', 'files', 'tools']

canvas = Canvas(BASEURL, TOKEN)

app = QApplication(sys.argv)
app.setAttribute(Qt.AA_UseHighDpiPixmaps)

main = QMainWindow()

tree = QTreeWidget()
tree.setHeaderLabels(['Course', 'Date Created'])
tree.setAlternatingRowColors(True)
tree.setColumnCount(2)
tree.header().setSectionResizeMode(QHeaderView.Stretch)

contentTypeComboBox = QComboBox()
contentTypeComboBox.addItem('Modules')
contentTypeComboBox.addItem('Filesystem')
contentTypeComboBox.addItem('External Tools')

contentTypeLayout = QHBoxLayout()
contentTypeLayout.addItem(QSpacerItem(20,40))
contentTypeLayout.addWidget(contentTypeComboBox)
contentTypeLayout.addItem(QSpacerItem(20,40))
contentTypeLayout.setStretch(0, 1)
contentTypeLayout.setStretch(1, 2)
contentTypeLayout.setStretch(2, 1)

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
controlLayout.addLayout(contentTypeLayout)
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

def add_courses(onlyFavorites, contentTypeIdx):
    contentType = CONTENT_TYPES[contentTypeIdx]

    favorites, others = get_courses_separated(canvas)

    for course in favorites:
        CourseItem(tree, object=course, content=contentType)

    if not onlyFavorites:
        SeparatorItem(tree)
        for course in others:
            CourseItem(tree, object=course, content=contentType)

def contentTypeChanged(idx):
    onlyFavorites = favoriteSlider.value()
    tree.clear()
    add_courses(onlyFavorites, idx)

def favoriteSliderChanged(onlyFavorites):
    idx = contentTypeComboBox.currentIndex()
    tree.clear()
    add_courses(onlyFavorites, idx)

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

add_courses(favoriteSlider.value(), contentTypeComboBox.currentIndex())

tree.itemDoubleClicked.connect(lambda item: item.dblClickFcn())

expandButton.clicked.connect(expand_all)
contentTypeComboBox.currentIndexChanged.connect(contentTypeChanged)
favoriteSlider.valueChanged.connect(favoriteSliderChanged)

app.topLevelWidgets()[0].setGeometry(
    QStyle.alignedRect(
        Qt.LeftToRight,
        Qt.AlignCenter,
        QSize(800,600),
        tree.screen().geometry())
)

main.show()

# app.topLevelWidgets()[0].setFocus()

if __name__ == '__main__':
    sys.exit(app.exec_())