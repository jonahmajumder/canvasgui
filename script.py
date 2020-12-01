import sys
from time import time

from canvasapi import Canvas
from canvasapi.exceptions import Unauthorized

from apistuff import *
from secrets import BASEURL, TOKEN

canvas = Canvas(BASEURL, TOKEN)

favorites, others = get_courses_separated(canvas)

if __name__ == '__main__':

    sa = favorites[2]

    for c in favorites:
        print(c.name)
        print('')
        for t in c.get_external_tools():
            print(t.name)
            print(t.get_sessionless_launch_url())
        print('')

