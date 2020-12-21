# Python Canvas (Courseworks) GUI

This project builds on the open-source Python package [CanvasAPI](https://github.com/ucfopen/canvasapi), which is itself built to interact with Instructure's RESTful [HTTP API](https://canvas.instructure.com/doc/api/index.html). Using this package (and Qt for Python), I have built an interactive app allowing a user to browse (and download) courses, files, assignments, and other content.

Below is a depiction of content from my own classes, viewed at the "module" level.

<img src="screenshot.png" width="600">

Login is accomplished by generation of an OAuth token (simplest online via your user profile page, as explained [here](https://canvas.instructure.com/doc/api/file.oauth.html#manual-token-generation)). That token, along with an institution-specific base URL, can be included in a file or entered manually.

The preferences file must be called "defaults.json" with the following keys:
```
"baseurl": <institution-specific url>
"token": <personal generated oauth token>
"downloadfolder": <path to a local folder>
"defaultcontent": <"modules", "files", "assignments", or "tools">
```
If any of these are deemed invalid (or no file is detected), a GUI will prompt the user to fill them in.

### Nonstandard Dependencies
(All available on PyPI)

- [PyQt5](https://pypi.org/project/PyQt5/)
- [CanvasAPI](https://pypi.org/project/canvasapi/)
- [dateutil](https://pypi.org/project/python-dateutil/)

### To do list:

- [X] Make app into class (rather than script)
- [X] Pereferences UI allowing specification of login credentials, download destination, default view
- [ ] Context menus for everything but expand
- [ ] Bulk download of files (module/folder level)
- [X] Automatic conversion of Excel files to PDFs (as with Word and Powerpoint files)
- [ ] Better column resizing
- [X] Convert from widget to model architecture
- [ ] Sorting by date
- [X] Select external tools from "tabs" rather than directly
- [ ] Replace terminal printed lines with dialog? Status bar?
- [X] Dealing with duplicate children
- [ ] Deployment into macOS (.app) standalone application
- [ ] Multithreaded retrieval of data for "expand all" (back burner)
