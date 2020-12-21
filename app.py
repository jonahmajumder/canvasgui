import sys
from time import time
import webbrowser
import base64

from PyQt5.Qt import *
from PyQt5.QtGui import *

from canvasapi import Canvas
from canvasapi.exceptions import Unauthorized

from guihelper import disp_html
from classdefs import CourseItem, SeparatorItem, SliderHLayout, CustomProxyModel, SORTROLE
from utils import Preferences
from appcontrol import set_term_title
from secrets import BASEURL, TOKEN


class CanvasApp(QMainWindow):
    SIZE = (800, 600)
    TITLE = 'Canvas Browser'

    def __init__(self, *args, **kwargs):
        super(QMainWindow, self).__init__(*args, **kwargs)

        # establish easy reference to running QApplication
        self.app = QApplication.instance()

        self.app.setAttribute(Qt.AA_UseHighDpiPixmaps)
        self.app.setWindowIcon(QIcon('icons/icon.icns'))
        self.setWindowTitle(self.TITLE)

        self.preferences = Preferences(self)

        if len(self.preferences.current) == 0:
            # this means no preferences (user closed pref window)
            print('No preferences!')
            sys.exit()

        self.canvas = Canvas(
            self.preferences.current['baseurl'],
            self.preferences.current['token']
        )
        self.user = self.canvas.get_current_user()

        self.addWidgets()

        # use preferences to set content type combo box
        self.contentTypeComboBox.setCurrentIndex(self.preferences.current['defaultcontent'])

        self.add_courses()

        self.connect_signals()

        # self.tree.sortByColumn(1, Qt.DescendingOrder) # most recent at top

        self.show()
        
        self.center_on_screen()

    def auth_get(self, url):
        return self.canvas._Canvas__requester.request('GET', _url=url)

# -------------------- INITIALIZATION METHODS --------------------

    def addWidgets(self):

        self.contentTypeComboBox = QComboBox()
        for ct in CourseItem.CONTENT_TYPES:
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

        self.tree = QTreeView()
        self.model = QStandardItemModel(0, 2, self)
        self.proxyModel = CustomProxyModel(self.model, favorites_initial=self.favoriteSlider.value())
        self.proxyModel.setSourceModel(self.model)
        self.model.setHorizontalHeaderLabels(['Course', 'Date Created'])
        self.tree.setAlternatingRowColors(True)
        self.tree.header().setSectionResizeMode(QHeaderView.Stretch)
        self.tree.setSortingEnabled(True)
        self.tree.setModel(self.proxyModel)
        self.tree.header().setSortIndicator(1, Qt.DescendingOrder)

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
        self.tree.doubleClicked.connect(self.tree_double_click)

        self.expandButton.clicked.connect(self.expand_all)
        self.contentTypeComboBox.currentIndexChanged.connect(self.contentTypeChanged)
        self.favoriteSlider.valueChanged.connect(self.proxyModel.only_favorites_changed)

    def tree_double_click(self, proxyindex):
        sourceindex = self.proxyModel.mapToSource(proxyindex)
        item = self.model.itemFromIndex(sourceindex)
        item.dblClickFcn(contentTypeIndex=self.contentTypeComboBox.currentIndex())

# -------------------- FUNCTIONAL METHODS --------------------

    def get_courses_separated(self):
        favorites = self.user.get_favorite_courses()
        favorite_ids = [c.id for c in favorites]
        all_courses = list(self.user.get_courses())
        others = [c for c in all_courses if c.id not in favorite_ids]
        return favorites, others

    def add_courses(self):
        favorites, others = self.get_courses_separated()

        root = self.model.invisibleRootItem()

        for course in favorites:
            item = CourseItem(object=course, favorite=True,
                downloadfolder=self.preferences.current['downloadfolder'])
            root.appendRow([item, item.date])

        for course in others:
            item = CourseItem(object=course, favorite=False,
                downloadfolder=self.preferences.current['downloadfolder'])
            root.appendRow([item, item.date])

    def clear_courses(self):
        self.model.removeRows(0, self.model.rowCount())

    def contentTypeChanged(self):
        self.clear_courses()
        self.add_courses()

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