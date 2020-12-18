# utils.py
from dateutil.parser import isoparse
from datetime import datetime
import pytz
from PyQt5.QtCore import QDateTime

class Date(object):
    """docstring for Date"""
    TIMEZONE = pytz.timezone('America/New_York')

    def __init__(self, canvasobj):
        super(Date, self).__init__()
        self.datetime = self.datetime_from_obj(canvasobj)

    @staticmethod
    def hasattr_not_none(obj, attr):
    # check if has attr and also if that attr is not-None
        if hasattr(obj, attr):
            if getattr(obj, attr) is not None:
                return True
            else:
                return False
        else:
            return False

    def datestr_from_obj(self, canvasobj):
        if self.hasattr_not_none(canvasobj, 'created_at'):
            return canvasobj.created_at
        elif self.hasattr_not_none(canvasobj, 'completed_at'):
            return canvasobj.completed_at
        elif self.hasattr_not_none(canvasobj, 'unlock_at'):
            return canvasobj.unlock_at
        elif self.hasattr_not_none(canvasobj, 'due_at'):
            return canvasobj.due_at
        elif self.hasattr_not_none(canvasobj, 'url'): # do this one last because can't try another after
            jsdata = get_item_data(canvasobj.url).json()
            if 'created_at' in jsdata:
                return jsdata['created_at']
            else:
                return None
        else:
            print('No date found!')
            print(repr(canvasobj))
            return None

    def datetime_from_obj(self, obj):
        s = self.datestr_from_obj(obj)
        if s is not None:
            # make datetime (which will be in UTC timc) and convert to EST
            return isoparse(s).astimezone(self.TIMEZONE)
        else:
            return None

    def smart_formatted(self):
        if self.datetime is not None:
            days_ago = (datetime.now().astimezone(self.TIMEZONE).date() - self.datetime.date()).days
            if days_ago == 0:
                daystring = 'Today'
            elif days_ago == 1:
                daystring = 'Yesterday'
            else:
                daystring = self.datetime.strftime('%b %-d, %Y')
            timestring = self.datetime.strftime('%-I:%M %p')
            return '{0} at {1}'.format(daystring, timestring)
        else:
            return ''

    def as_qdt(self):
        if self.datetime is not None:
            secs = self.datetime.timestamp() # seconds since epoch
            return QDateTime.fromSecsSinceEpoch(secs)
        else:
            return None


class Preferences(object):
    """docstring for Preferences"""
    def __init__(self, arg):
        super(Preferences, self).__init__()
        self.arg = arg
        