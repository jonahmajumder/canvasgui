from subprocess import Popen, PIPE, run
from pathlib import Path
import os  

def run_osascript(script, args=[]):
    p = Popen(['osascript', '-'] + args, stdin=PIPE, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    stdout, stderr = p.communicate(script)
    return stdout

termtitle = """
tell application "Terminal" to set custom title of first window to "{}"
"""

def set_term_title(title):
    run_osascript(termtitle.format(title))

wordscript = """
tell application "Microsoft Word"
    launch
    open file "{0}"
    tell active document
        save as it file name "{1}" file format format PDF
        close saving no
    end tell
    quit
end tell
"""
pptscript = """
tell application "Microsoft PowerPoint"
    launch
    open file "{0}"
    tell active presentation
        save in "{1}" as save as PDF
        close saving no
    end tell
    quit
end tell
"""
excelscript = """
set PDFPath to "{1}"
tell application "Microsoft Excel"
    launch
    open file "{0}"
    alias PDFPath
    tell page setup object of active sheet
        set page orientation to landscape
        set zoom to false
        set fit to pages wide to 1
        set fit to pages tall to 9999
    end tell
    save as active sheet filename PDFPath file format PDF file format
    close active workbook saving no
    quit
end tell
"""

def convert(*args):
    infile = Path(args[0])
    if infile.suffix in ['.doc', '.docx']:
        script = wordscript
    elif infile.suffix in ['.ppt', '.pptx']:
        script = pptscript
    elif infile.suffix in ['.xls', '.xlsx']:
        script = excelscript
    else:
        raise Exception('Unhandled file extension!')

    if len(args) < 2:
        outfile = infile.with_suffix('.pdf')
    else:
        outfile = args[1]

    infile_asform = ('Macintosh HD' + str(infile)).replace(os.path.sep, ':')
    outfile_asform = ('Macintosh HD' + str(outfile)).replace(os.path.sep, ':')

    formatted = script.format(infile_asform, outfile_asform)
    # print(formatted)
    ret = run_osascript(formatted)

if __name__ == '__main__':
     f = '/Users/jonahmajumder/Downloads/Case 2 WES.xlsx'
     convert(f)
