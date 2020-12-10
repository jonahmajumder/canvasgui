# Python Canvas (Courseworks) GUI

This project builds on the open-source Python package [CanvasAPI](https://github.com/ucfopen/canvasapi), which is itself built to interact with Instructure's RESTful [HTTP API](https://canvas.instructure.com/doc/api/index.html). Using this package (and Qt for Python), I have built an interactive app allowing a user to browse (and download) courses, files, assignments, and other content.

Below is a depiction of content from my own classes, viewed at the "module" level.

<img src="screenshot.png" width="600">

Login is currently accomplished by generation of an OAuth token (simplest online via your user profile page, as explained [here](https://canvas.instructure.com/doc/api/file.oauth.html#manual-token-generation)). That token, along with an institution-specific base URL, is included in a "secret" file.

### To do list:

- [X] Make app into class (rather than script)
- [ ] Interactive login (rather than just by file with credentials)
- [X] Automatic conversion of Excel files to PDFs (as with Word and Powerpoint files)
- [ ] Better column resizing
- [ ] Sorting by date (with smart date display)
- [X] Select external tools from "tabs" rather than directly
- [ ] Dialogs instead of terminal printed lines
- [ ] Dealing with duplicate children
