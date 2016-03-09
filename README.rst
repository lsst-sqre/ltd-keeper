#####################
LSST the Docs: Keeper
#####################

**Keeper** is a web app for managing LSST software documenting published with the **LSST the Docs** (LTD) platform.
You can learn more about LTD in our `SQR-006`_ technote.

Keeper provides a RESTful API that is used by `LTD Mason <https://github.com/lsst-sqre/ltd-mason>`_ for publishing new documentation, and by the document web pages to help users discover and switch between versions of the docs.
Keeper is implemented as a Python `Flask <http://flask.pocoo.org>`_ app.

Docs
====

**Read the docs at http://ltd-keeper.lsst.io**.

The documentation covers both the REST API consumption and DevOps perspectives.

****

Copyright 2016 AURA/LSST, MIT License.

Parts of this codebase are based on `miguelgrinberg/oreilly-flask-apis-video <https://github.com/miguelgrinberg/oreilly-flask-apis-video>`_;
Copyright 2014 Miguel Grinberg, MIT License.

.. _SQR-006: http://sqr-006.lsst.io
