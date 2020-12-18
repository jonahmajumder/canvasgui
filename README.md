# Python Canvas (Courseworks) GUI

This project builds on the open-source Python package [CanvasAPI](https://github.com/ucfopen/canvasapi), which is itself built to interact with Instructure's RESTful [HTTP API](https://canvas.instructure.com/doc/api/index.html). Using this package (and Qt for Python), I have built an interactive app allowing a user to browse (and download) courses, files, assignments, and other content.

Below is a depiction of content from my own classes, viewed at the "module" level.

<img src="screenshot.png" width="600">

Login is accomplished by generation of an OAuth token (simplest online via your user profile page, as explained [here](https://canvas.instructure.com/doc/api/file.oauth.html#manual-token-generation)). That token, along with an institution-specific base URL, is currently included in a dedicated file.

### Nonstandard Dependencies
(All available on PyPI)

- [PyQt5](https://pypi.org/project/PyQt5/)
- [CanvasAPI](https://pypi.org/project/canvasapi/)
- [dateutil](https://pypi.org/project/python-dateutil/1.4/)

### To do list:

- [X] Make app into class (rather than script)
- [ ] Pereferences UI allowing specification of login credentials, download destination, whether to show only favorite classes(?)
- [ ] Context menus for everything but expand
- [ ] Bulk download of files (module/folder level)
- [X] Automatic conversion of Excel files to PDFs (as with Word and Powerpoint files)
- [ ] Better column resizing
- [ ] Sorting by date (probably convert from widget to model view)
- [X] Select external tools from "tabs" rather than directly
- [ ] Dialogs instead of terminal printed lines
- [ ] Dealing with duplicate children
- [ ] Deployment into macOS (.app) standalone application
- [ ] Multithreaded retrieval of data for "expand all" (back burner)
