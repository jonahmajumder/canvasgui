import sys
from time import time
import webbrowser

from PyQt5.Qt import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from canvasapi import Canvas
from canvasapi.exceptions import Unauthorized
from apistuff import *

class SeparatorItem(QTreeWidgetItem):
    """
    class to serve as divider (no functionality)
    """
    def __init__(self, *args, **kwargs):
        super(SeparatorItem, self).__init__(*args, **kwargs)

        self.setFlags(Qt.NoItemFlags)

        # self.setBackground(0, QBrush(QColor('black')))
        # self.setBackground(1, QBrush(QColor('black')))

    def dblClickFcn(self):
        pass

class DoubleClickHandler():
    """
    parent class to handle double click activity (not intended to be instantiated alone)
    """
    def __init__(self):

        self.dblClicks = 0

        self.dblClickActions = []
        if hasattr(self, 'expand'):
            self.dblClickActions.append(self.expand)
        if hasattr(self, 'open'):
            self.dblClickActions.append(self.open)
        else:
            self.dblClickActions.append(lambda: None) # make last is not expand

    def dblClickFcn(self, **kwargs):
        nclicks = self.dblClicks
        self.dblClicks += 1
        if nclicks < len(self.dblClickActions) - 1:
            self.dblClickActions[nclicks](**kwargs) # execute function
        else:
            self.dblClickActions[-1](**kwargs) # execute last function repeatedly
        
        # print('Double clicks: {}'.format(nclicks))


class CanvasItem(QTreeWidgetItem, DoubleClickHandler):
    """
    general parent class for tree elements with corresponding canvasapi objects
    """
    def __init__(self, *args, **kwargs):
        self.obj = kwargs.pop('object', None)
        super(CanvasItem, self).__init__(*args, **kwargs)
        super(DoubleClickHandler, self).__init__()
        # print(repr(self.obj))
        if hasattr(self.obj, 'name'):
            self.setText(0, self.obj.name)
        elif hasattr(self.obj, 'title'):
            self.setText(0, self.obj.title)
        elif hasattr(self.obj, 'display_name'):
            self.setText(0, self.obj.display_name)
        else:
            self.setText(0, str(self.obj))

        datestr = get_date_string(self.obj)
        self.created = parse_date_string(datestr)

        self.setText(1, format_date(self.created))

        # self.dblClicks = 0

        # self.dblClickActions = []
        # if hasattr(self, 'expand'):
        #     self.dblClickActions.append(self.expand)
        # if hasattr(self, 'open'):
        #     self.dblClickActions.append(self.open)
        # self.dblClickActions.append(lambda: None)

    # def dblClickFcn(self):
    #     if self.dblClicks < len(self.dblClickActions) - 1:
    #         self.dblClickActions[self.dblClicks]() # execute function
    #     else:
    #         self.dblClickActions[-1]() # execute last function repeatedly
    #     self.dblClicks += 1

class CourseItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "course" objects
    """
    def __init__(self, *args, **kwargs):
        self.modules = kwargs.pop('modules', False)
        super(CourseItem, self).__init__(*args, **kwargs)

        self.setIcon(0, QIcon('book.png'))

    def expand(self, **kwargs):
        if self.modules:
            self.get_modules()
        else:
            self.get_filesystem()

    def get_modules(self):
        for m in self.obj.get_modules():
            ModuleItem(self, object=m)

    def get_filesystem(self):
        root = get_root_folder(self.obj)

        files = safe_get_files(root)
        folders = safe_get_folders(root)

        if len(files + folders) > 0:
            for file in safe_get_files(root):
                FileItem(self, object=file)
            
            for folder in safe_get_folders(root):
                FolderItem(self, object=folder)
        else:
            self.setDisabled(True)

class ModuleItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "module" objects
    """
    def __init__(self, *args, **kwargs):
        super(ModuleItem, self).__init__(*args, **kwargs)

        self.setIcon(0, QIcon('module.png'))

    def expand(self, **kwargs):
        items = list(self.obj.get_module_items())
        for mi in items:
            if mi.type == 'SubHeader':
                pass
            elif mi.type == 'File':
                ModuleFileItem(self, object=mi)
            elif mi.type == 'Page':
                ModulePageItem(self, object=mi)
            else:
                ModuleDummyItem(self, object=mi)
        if len(items) == 0:
            self.setDisabled(True)

class ModuleFileItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "moduleitem" objects with type "file"
    """
    def __init__(self, *args, **kwargs):
        super(ModuleFileItem, self).__init__(*args, **kwargs)

        self.setIcon(0, QIcon('file.png'))

    def open(self, **kwargs):
        download_module_file(self.obj)

class ModulePageItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "moduleitem" objects with type "page"
    """
    def __init__(self, *args, **kwargs):
        super(ModulePageItem, self).__init__(*args, **kwargs)

        self.setIcon(0, QIcon('html.png'))

    def expand(self, **kwargs):
        advance = kwargs.get('advance', True)

        links = get_module_page_links(self.obj)
        # print(self.text(0))
        # print('Link types: ' + str(list(links.keys())))
        # print('')
        files = links.get('File', [])
        pages = links.get('Page', [])
        quizzes = links.get('Quiz', [])
        assignments = links.get('Assignment', [])

        for a in files:
            LinkedFileItem(self, element=a)
        for a in pages:
            LinkedPageItem(self, element=a)
        for a in quizzes + assignments:
            LinkedQuizItem(self, element=a)
        if not sum(links.values(), []):
            if advance:
                self.dblClickFcn() # no action for expand, send another click

    def open(self, **kwargs):
        body = get_module_page_html(self.obj)
        disp_html(body)


class ModuleDummyItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "moduleitem" objects with other types
    (many are an assigment-like item)
    """
    def __init__(self, *args, **kwargs):
        super(ModuleDummyItem, self).__init__(*args, **kwargs)

        self.setIcon(0, QIcon('assigment.png'))

    def open(self, **kwargs):
        if hasattr(self.obj, 'url'):
            r = get_item_data(self.obj.url)
            js = r.json()
            if 'url' in js:
                r = get_item_data(js['url'])
                print('Opening {}.'.format(self.obj.title))
                webbrowser.open(r.json()['url'])

class FolderItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "folder" objects
    """
    def __init__(self, *args, **kwargs):
        super(FolderItem, self).__init__(*args, **kwargs)

        self.setIcon(0, QIcon('folder.png'))

    def expand(self, **kwargs):
        for file in safe_get_files(self.obj):
            FileItem(self, object=file)

        for folder in safe_get_folders(self.obj):
            FolderItem(self, object=folder)

class FileItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "file" objects (within folders)
    """
    def __init__(self, *args, **kwargs):
        super(FileItem, self).__init__(*args, **kwargs)

        self.setIcon(0, QIcon('file.png'))

    def open(self, **kwargs):
        download_file(self.obj)

class LinkedFileItem(QTreeWidgetItem, DoubleClickHandler):
    """
    class for tree elements corresponding to files linked on "module pages"
    (no canvasapi object, but instead bs4 element from html; file can be downloaded)
    """
    def __init__(self, *args, **kwargs):
        self.elem = kwargs.pop('element', None)
        super(LinkedFileItem, self).__init__(*args, **kwargs)
        super(DoubleClickHandler, self).__init__()

        self.setIcon(0, QIcon('file.png'))

        title = parse_title_from_link(self.elem.attrs)
        self.setText(0, title)
        
    def open(self, **kwargs):
        download_module_linked_file(self.elem.attrs)

class LinkedPageItem(QTreeWidgetItem, DoubleClickHandler):
    """
    class for tree elements corresponding to (internal) pages linked on "module pages"
    (no canvasapi object, but instead bs4 element from html)
    """
    def __init__(self, *args, **kwargs):
        self.elem = kwargs.pop('element', None)
        super(LinkedPageItem, self).__init__(*args, **kwargs)
        super(DoubleClickHandler, self).__init__()

        self.setIcon(0, QIcon('html.png'))
        
        title = parse_title_from_link(self.elem.attrs)
        self.setText(0, title)

    def open(self, **kwargs):
        js = get_module_linked_page(self.elem.attrs)
        if 'body' in js:
            disp_html(js['body'])

class LinkedQuizItem(QTreeWidgetItem, DoubleClickHandler):
    """
    class for tree elements corresponding to (internal) pages linked on "module pages"
    (no canvasapi object, but instead bs4 element from html)
    """
    def __init__(self, *args, **kwargs):
        self.elem = kwargs.pop('element', None)
        super(LinkedQuizItem, self).__init__(*args, **kwargs)
        super(DoubleClickHandler, self).__init__()

        self.setIcon(0, QIcon('assigment.png'))
        
        title = parse_title_from_link(self.elem.attrs)
        self.setText(0, title)

    def open(self, **kwargs):
        js = get_module_linked_page(self.elem.attrs)
        webbrowser.open(js['html_url'])
            

class SliderHLayout(QHBoxLayout):
    """
    hlayout with labels on left and right, with 2 choices
    """
    valueChanged = pyqtSignal(bool)

    def __init__(self, *args, **kwargs):
        arglist = list(args)
        if len(arglist) >= 2:
            self.falseLabelText = arglist.pop(0)
            self.trueLabelText = arglist.pop(0)
            newargs = tuple(arglist)
        else:
            raise Exception('Slider needs 2 labels!')

        self.startVal = kwargs.pop('startVal', False)

        super(QHBoxLayout, self).__init__(*newargs, **kwargs)

        self.addFalseLabel()
        self.addSlider()
        self.addTrueLabel()

        self.setWidths()

        self.setValue(self.startVal)

        self.slider.valueChanged.connect(self.sliderValueChangedFcn)

    def addSlider(self):
        self.slider = QSlider()
        self.slider.setOrientation(Qt.Horizontal)
        self.slider.setMaximum(1)
        self.slider.setSingleStep(1)
        self.slider.setPageStep(1)
        self.addWidget(self.slider)

    def addFalseLabel(self):
        self.falseLabel = QLabel(self.falseLabelText)
        self.falseLabel.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.addWidget(self.falseLabel)

    def addTrueLabel(self):
        self.trueLabel = QLabel(self.trueLabelText)
        self.trueLabel.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.addWidget(self.trueLabel)

    def setWidths(self):
        self.setStretch(0, 2)
        self.setStretch(1, 1)
        self.setStretch(2, 2)

    def setValue(self, boolVal):
        self.slider.setValue(int(boolVal))

    def value(self):
        return bool(self.slider.value())

    def sliderValueChangedFcn(self, int):
        self.valueChanged.emit(bool(int))





