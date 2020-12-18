import sys
from time import time
import webbrowser
import base64

from PyQt5.Qt import *
from PyQt5.QtGui import *

from canvasapi import Canvas
from canvasapi.exceptions import Unauthorized

from guihelper import disp_html
from classdefs import CourseItem, SeparatorItem, SliderHLayout
from appcontrol import set_term_title
from secrets import BASEURL, TOKEN

class CanvasApp(QMainWindow):
    CONTENT_TYPES = [
        {'tag': 'modules', 'displayname': 'Modules'},
        {'tag': 'files', 'displayname': 'Filesystem'},
        {'tag': 'assignments', 'displayname': 'Assignments'},
        {'tag': 'tools', 'displayname': 'External Tools'}
    ]
    SIZE = (800, 600)
    TITLE = 'Canvas Browser'

    def __init__(self, *args, **kwargs):
        super(QMainWindow, self).__init__(*args, **kwargs)

        # establish easy reference to running QApplication
        self.app = QApplication.instance()

        self.app.setAttribute(Qt.AA_UseHighDpiPixmaps)
        self.app.setWindowIcon(QIcon('icons/icon.icns'))
        self.setWindowTitle(self.TITLE)

        self.canvas = Canvas(BASEURL, TOKEN)
        self.user = self.canvas.get_current_user()

        self.addWidgets()

        self.add_courses(self.favoriteSlider.value(), self.contentTypeComboBox.currentIndex())

        self.connect_signals()

        self.tree.setSortingEnabled(True)
        # self.tree.sortByColumn(1, Qt.DescendingOrder) # most recent at top

        self.show()
        
        self.center_on_screen()

    def auth_get(self, url):
        return self.canvas._Canvas__requester.request('GET', _url=url)

# -------------------- INITIALIZATION METHODS --------------------

    def addWidgets(self):

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(['Course', 'Date Created'])
        self.tree.setAlternatingRowColors(True)
        self.tree.setColumnCount(2)
        self.tree.header().setSectionResizeMode(QHeaderView.Stretch)

        self.contentTypeComboBox = QComboBox()
        for ct in self.CONTENT_TYPES:
            self.contentTypeComboBox.addItem(ct['displayname'])

        self.contentTypeLayout = QHBoxLayout()
        self.contentTypeLayout.addItem(QSpacerItem(20,40))
        self.contentTypeLayout.addWidget(self.contentTypeComboBox)
        self.contentTypeLayout.addItem(QSpacerItem(20,40))
        self.contentTypeLayout.setStretch(0, 1)
        self.contentTypeLayout.setStretch(1, 2)
        self.contentTypeLayout.setStretch(2, 1)

        self.favoriteSlider = SliderHLayout('All Courses', 'Favorites', startVal=True)

        self.expandButton = QPushButton('Expand All')

        self.expandLayout = QHBoxLayout()
        self.expandLayout.addItem(QSpacerItem(20,40))
        self.expandLayout.addWidget(self.expandButton)
        self.expandLayout.addItem(QSpacerItem(20,40))
        self.expandLayout.setStretch(0, 1)
        self.expandLayout.setStretch(1, 1)
        self.expandLayout.setStretch(2, 1)

        self.mainLayout = QVBoxLayout()

        self.controlLayout = QHBoxLayout()
        self.controlLayout.addLayout(self.contentTypeLayout)
        self.controlLayout.addLayout(self.favoriteSlider)
        self.controlLayout.addLayout(self.expandLayout)
        self.controlLayout.setStretch(0, 1)
        self.controlLayout.setStretch(1, 1)
        self.controlLayout.setStretch(2, 1)

        self.mainLayout.addLayout(self.controlLayout)
        self.mainLayout.addWidget(self.tree)

        self.central = QWidget()
        self.central.setLayout(self.mainLayout)
        self.setCentralWidget(self.central)

    def center_on_screen(self):
        self.setGeometry(
            QStyle.alignedRect(
                Qt.LeftToRight,
                Qt.AlignCenter,
                QSize(*self.SIZE),
                self.screen().geometry() # rectangle to center to
            )
        )

    def connect_signals(self):
        self.tree.itemDoubleClicked.connect(lambda item: item.dblClickFcn())

        self.expandButton.clicked.connect(self.expand_all)
        self.contentTypeComboBox.currentIndexChanged.connect(self.contentTypeChanged)
        self.favoriteSlider.valueChanged.connect(self.favoriteSliderChanged)

# -------------------- FUNCTIONAL METHODS --------------------

    def get_courses_separated(self):
        favorites = self.user.get_favorite_courses()
        favorite_ids = [c.id for c in favorites]
        all_courses = list(self.user.get_courses())
        others = [c for c in all_courses if c.id not in favorite_ids]
        return favorites, others

    def add_courses(self, onlyFavorites, contentTypeIdx):
        contentType = self.CONTENT_TYPES[contentTypeIdx]['tag']

        favorites, others = self.get_courses_separated()

        for course in favorites:
            CourseItem(self.tree, object=course, content=contentType)

        if not onlyFavorites:
            SeparatorItem(self.tree)
            for course in others:
                CourseItem(self.tree, object=course, content=contentType)

    def contentTypeChanged(self, idx):
        onlyFavorites = self.favoriteSlider.value()
        self.tree.clear()
        self.add_courses(onlyFavorites, idx)

    def favoriteSliderChanged(self, onlyFavorites):
        idx = self.contentTypeComboBox.currentIndex()
        self.tree.clear()
        self.add_courses(onlyFavorites, idx)

    def expand_children(self, item):
        for i in range(item.childCount()):
            ch = item.child(i)
            if hasattr(ch, 'expand'):
                ch.dblClickFcn(advance=False)
            expand_children(ch)

    def expand_all(self):
        start_time = time()
        self.expand_children(self.tree.invisibleRootItem())
        print('Load time: {:.2f}'.format(time() - start_time))

    def generate_profile_html(self):
        data = self.user.get_profile()

        html = '<div align="center">'
        if 'name' in data:
            html += '<h1>{}</h1>'.format(data['name'])     
        if 'avatar_url' in data:
            img_content = self.auth_get(data['avatar_url']).content
            img_data_uri = base64.b64encode(img_content).decode('utf-8')
            html += '<br><img src="data:image/png;base64,{}">'.format(img_data_uri)
        if 'primary_email' in data:
            html += '<h3>Email: {}</h3>'.format(data['primary_email'])
        if 'login_id' in data:
            html += '<h3>Login: {}</h3>'.format(data['login_id'])
        if 'bio' in data:
            html += '<p>{}</p>'.format(data['bio'])
        html += '</div>'

        return html

    def show_user(self):
        htmlstr = self.generate_profile_html()
        disp_html(htmlstr, title='Current User')

# set_term_title(CanvasApp.TITLE)

app = QApplication(sys.argv)
gui = CanvasApp()

if __name__ == '__main__':
    sys.exit(app.exec_()) # block until app exits