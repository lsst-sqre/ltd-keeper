#####################
LSST the Docs: Keeper
#####################

**Keeper** is a web app for managing LSST software documenting published with the **LSST the Docs** (LTD) platform.
You can learn more about LTD in our `SQR-006`_ technote.

Keeper provides a RESTful API that is used by `ltd-mason <https://github.com/lsst-sqre/ltd-mason>`_ for publishing new documentation, and by the document web pages to help users discover and switch between versions of the docs.
Keeper is implemented as a Python `Flask <http://flask.pocoo.org>`_ app.

****

Copyright 2016 AURA/LSST.

License: MIT.

.. _SQR-006: http://sqr-006.lsst.io
