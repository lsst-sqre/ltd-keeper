#####################
LSST the Docs: Keeper
#####################

**Keeper** is a web app for managing LSST software documenting published with the **LSST the Docs** (LTD) platform.
You can learn more about LTD in our `SQR-006`_ technote.

Keeper provides a RESTful API that is used by `LTD Mason <https://github.com/lsst-sqre/ltd-mason>`_ for publishing new documentation, and by the document web pages to help users discover and switch between versions of the docs.
Keeper is implemented as a Python `Flask <http://flask.pocoo.org>`_ app.

Docs
====

**Read the docs at https://ltd-keeper.lsst.io**.

The documentation covers both the REST API consumption and DevOps perspectives.

****

Copyright 2016–2017 Association of Universities for Research in Astronomy, Inc.

MIT license. See the LICENSE file. See also licenses/ for licenses of third-party code.

.. _SQR-006: https://sqr-006.lsst.io
