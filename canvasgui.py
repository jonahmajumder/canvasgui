import sys
from time import time
import webbrowser

from PyQt5.Qt import *
from PyQt5.QtGui import *

from canvasapi import Canvas
from canvasapi.exceptions import Unauthorized

from apistuff import *
from classdefs import *

ASMODULES = False

ONLYNICKNAMED = True


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

nicknameSlider = SliderHLayout('All Courses', 'Nicknamed Courses', startVal=False)

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
controlLayout.addLayout(nicknameSlider)
controlLayout.addLayout(expandLayout)
controlLayout.setStretch(0, 1)
controlLayout.setStretch(1, 1)
controlLayout.setStretch(2, 1)

mainLayout.addLayout(controlLayout)
mainLayout.addWidget(tree)

central = QWidget()
central.setLayout(mainLayout)
main.setCentralWidget(central)

def add_courses(onlyNicknamed, asModules):
    nicknamed_courses, non_nicknamed_courses = get_courses_separated(canvas)

    for course in nicknamed_courses:
        CourseItem(tree, object=course, modules=asModules)

    if not onlyNicknamed:
        SeparatorItem(tree)
        for course in non_nicknamed_courses:
            CourseItem(tree, object=course, modules=asModules)
    
def moduleSliderChanged(asModules):
    nicknamedOnly = nicknameSlider.value()
    tree.clear()
    add_courses(nicknamedOnly, asModules)

def nicknameSliderChanged(nicknamedOnly):
    asModules = moduleSlider.value()
    tree.clear()
    add_courses(nicknamedOnly, asModules)

def expand_children(item):
    for i in range(item.childCount()):
        ch = item.child(i)
        ch.callExpand()
        expand_children(ch)

def expand_all():
    start_time = time()
    expand_children(tree.invisibleRootItem())
    print('Load time: {:.2f}'.format(time() - start_time))

add_courses(nicknameSlider.value(), moduleSlider.value())

tree.itemDoubleClicked.connect(lambda item: item.dblClickFcn())

expandButton.clicked.connect(expand_all)
moduleSlider.valueChanged.connect(moduleSliderChanged)
nicknameSlider.valueChanged.connect(nicknameSliderChanged)

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