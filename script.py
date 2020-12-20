import sys
from time import time

from canvasapi import Canvas
from canvasapi.exceptions import Unauthorized

from secrets import BASEURL, TOKEN

canvas = Canvas(BASEURL, TOKEN)

# favorites, others = canvas.get_current_user()



