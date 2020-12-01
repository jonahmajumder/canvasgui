from subprocess import Popen, PIPE
from pathlib import Path
import os

def run_osascript(script, args=[]):
    p = Popen(['osascript', '-'] + args, stdin=PIPE, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    stdout, stderr = p.communicate(script)
    return stdout


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

def convert(*args):
    infile = Path(args[0])
    if infile.suffix in ['.doc', '.docx']:
        script = wordscript
    elif infile.suffix in ['.ppt', '.pptx']:
        script = pptscript
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
    run_osascript(formatted)

if __name__ == '__main__':
     f = '/Users/jonahmajumder/Downloads/07 - Lipid membrane structure.ppt'
     convert(f)
