import markdown
from bs4 import BeautifulSoup
import re
from pathlib import Path

parent = Path(__file__).parent

filename = 'README'
mdfile = str(parent / '{}.md'.format(filename))
htmlfile = str(parent / '{}.html'.format(filename))

with open(mdfile, 'r') as file:
    html = markdown.markdown(file.read())

soup = BeautifulSoup(html, 'html.parser')

imgs = soup.find_all('img')
for img in imgs:
    img['src'] = str(parent / img['src'])

checked = soup.find_all('li', text=re.compile(r'\[X\].*'))
unchecked = soup.find_all('li', text=re.compile(r'\[ \].*'))

for li in checked:
    li['class'] = 'checkbox'

for li in unchecked:
    li['class'] = 'checkbox'
    li.string = str(li.string).replace('[ ]', '[&nbsp;&nbsp;]')

styletag = soup.new_tag('style', type='text/css')

css = """
li.checkbox {
    list-style-type: none;
}
"""

styletag.string = css

soup.insert(0, styletag)

with open(htmlfile, 'w') as file:
    file.write(soup.prettify(formatter=None))