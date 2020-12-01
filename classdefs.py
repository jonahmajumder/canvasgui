import sys
from time import time

from PyQt5.Qt import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from canvasapi import Canvas
from canvasapi.exceptions import Unauthorized
from apistuff import *

def topmost_parent(widgetitem):
    p = widgetitem.parent()
    if p is None:
        return widgetitem
    else:
        return topmost_parent(p)

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
        if datestr:
            self.created = parse_date_string(datestr)
        else:
            self.created = self.parent().created

        # self.setText(1, format_date(self.created))
        self.setText(1, str(self.created))

    def course(self):
        return topmost_parent(self)

class CourseItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "course" objects
    """
    def __init__(self, *args, **kwargs):
        self.content = kwargs.pop('content', 'files')
        super(CourseItem, self).__init__(*args, **kwargs)

        self.setIcon(0, QIcon('book.png'))

    def expand(self, **kwargs):
        if self.content == 'files':
            self.get_filesystem()
        elif self.content == 'modules':
            self.get_modules()
        elif self.content == 'assignments':
            self.get_assignments()
        elif self.content == 'tools':
            self.get_tools()
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
            for file in files:
                FileItem(self, object=file)
            
            for folder in folders:
                FolderItem(self, object=folder)
        else:
            self.setDisabled(True)

    def get_assignments(self):
        for a in self.obj.get_assignments():
            AssignmentItem(self, object=a)

    def get_tools(self):
        for t in self.obj.get_external_tools():
            ExternalToolItem(self, object=t)

    def safe_get_item(self, method, id):
        try:
            return getattr(self.obj, method)(id)
        except Unauthorized:
            print('Unauthorized!')
            return None

class ExternalToolItem(CanvasItem):

    def __init__(self, *args, **kwargs):
        super(ExternalToolItem, self).__init__(*args, **kwargs)

        self.setIcon(0, QIcon('link.png'))

    def expand(self, **kwargs):
        if 'url' in self.obj.custom_fields:
            open_and_notify(self.obj.custom_fields['url'])
        else:
            print('No external url found!')
            # print('')
            # print(repr(self.obj))

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
                file = self.course().safe_get_item('get_file', mi.content_id)
                if file:
                    FileItem(self, object=file)
            elif mi.type == 'Page':
                page = self.course().safe_get_item('get_page', mi.page_url)
                if page:
                    PageItem(self, object=page)
            elif mi.type == 'Discussion':
                discussion = self.course().safe_get_item('get_discussion_topic', mi.content_id)
                if discussion:
                    DiscussionItem(self, object=discussion)
            elif mi.type == 'Quiz':
                quiz = self.course().safe_get_item('get_quiz', mi.content_id)
                if quiz:
                    QuizItem(self, object=quiz)
            elif mi.type == 'Assignment':
                assignment = self.course().safe_get_item('get_assignment', mi.content_id)
                if assignment:
                    AssignmentItem(self, object=assignment)
            else:
                print(repr(mi))
                DummyItem(self, object=mi)
        if len(items) == 0:
            self.setDisabled(True)

class DummyItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "moduleitem" objects
    this class should only be instantiated when an "unknown" type is encountered
    """
    def __init__(self, *args, **kwargs):
        super(DummyItem, self).__init__(*args, **kwargs)

    def open(self, **kwargs):
        if hasattr(self.obj, 'url'):
            r = get_item_data(self.obj.url)
            js = r.json()
            if 'url' in js:
                r = get_item_data(js['url'])
                open_and_notify(r.json()['url'])

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

class PageItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "page" objects
    """
    def __init__(self, *args, **kwargs):
        super(PageItem, self).__init__(*args, **kwargs)

        self.setIcon(0, QIcon('html.png'))

    def expand(self, **kwargs):
        advance = kwargs.get('advance', True)

        links = get_page_links(self.obj)
        # print(self.text(0))
        # print('Link types: ' + str(list(links.keys())))
        # print('')
        files = links.get('File', [])
        pages = links.get('Page', [])
        quizzes = links.get('Quiz', [])
        assignments = links.get('Assignment', [])

        # for a in sum(links.values(), []):
        #     info = parse_api_url(a.attrs['data-api-endpoint'])

        for a in files:
            info = parse_api_url(a.attrs['data-api-endpoint'])
            file = self.course().safe_get_item('get_file', info['files'])
            if file:
                FileItem(self, object=file)
        for a in pages:
            info = parse_api_url(a.attrs['data-api-endpoint'])
            page = self.course().safe_get_item('get_page', info['pages'])
            if page:
                PageItem(self, object=page)
        for a in quizzes:
            info = parse_api_url(a.attrs['data-api-endpoint'])
            quiz = self.course().safe_get_item('get_quiz', info['quizzes'])
            if quiz:
                QuizItem(self, object=quiz)
        for a in assignments:
            info = parse_api_url(a.attrs['data-api-endpoint'])
            assignment = self.course().safe_get_item('get_assignment', info['assignments'])
            if assignment:
                AssignmentItem(self, object=assignment)
        if not sum(links.values(), []):
            if advance:
                self.dblClickFcn() # no action for expand, send another click

    def open(self, **kwargs):
        if self.obj.body:
            disp_html(self.obj.body)
        else:
            print('No content on page.')

class QuizItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "quiz" objects
    """
    def __init__(self, *args, **kwargs):
        super(QuizItem, self).__init__(*args, **kwargs)

        self.setIcon(0, QIcon('quiz.png'))

    def open(self, **kwargs):
        open_and_notify(self.obj.html_url)

class DiscussionItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "discussiontopic" objects
    """
    def __init__(self, *args, **kwargs):
        super(DiscussionItem, self).__init__(*args, **kwargs)

        self.setIcon(0, QIcon('discussion.png'))

    def open(self, **kwargs):
        disp_html(self.obj.message)

class AssignmentItem(CanvasItem):
    """
    class for tree elements with corresponding canvasapi "discussiontopic" objects
    """
    def __init__(self, *args, **kwargs):
        super(AssignmentItem, self).__init__(*args, **kwargs)

        self.setIcon(0, QIcon('assignment.png'))

    def open(self, **kwargs):
        if hasattr(self.obj, 'url'):
            d = get_item_data(self.obj.url)
            pagetype = d.headers['content-type'].split(';')[0]
            if pagetype == 'application/json':
                if 'url' in d.json():
                    open_and_notify(d.json()['url'])
                else:
                    # revert to html url because this is json
                    open_and_notify(self.obj.html_url)
            else:
                open_and_notify(self.obj.url)
        else:
            open_and_notify(self.obj.html_url)


# ----------------------------------------------------------------------
            

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





