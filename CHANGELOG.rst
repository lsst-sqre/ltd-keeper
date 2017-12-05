##########
Change log
##########

1.6.0 (2017-12-13)
==================

- Migrate to setuptools-based packaging.
  LTD Keeper is now ``pip install``\ 'd into the Docker image at build time using the local sdist distribution (there are no plans to put LTD Keeper itself on PyPI).

- Use `setuptools_scm <https://github.com/pypa/setuptools_scm/>`__ to automatically establish the application version based on the Git tag.

- Automate the creation of the Docker image in Travis CI.
  The image is tagged with the branch or tag name.
  The build for the ``master`` branch is labeled as ``latest``.

- Build and testing are coordinated with a brand new Makefile.

`DM-12914 <https://jira.lsstcorp.org/browse/DM-12914>`__.

1.5.0 (2017-12-13)
==================

Added the explicit idea of tracking modes to edition resources.
This determines whether or not an edition is updated with a new build.
The mode is set with the ``mode`` field of the ``/products/<product>/edition`` resource.

The default tracking mode (``git_refs``) is to update if a build resource has the right git ref (a tag or branch name).

The new ``lsst_doc`` tracking mode allows an edition to watch for builds with git refs formatted as ``v<Major>.<Minor>`` and always publish the newest such tag.
This supports the revised LSST DM document release procedure: https://developer.lsst.io/v/DM-11952/docs/change-controlled-docs.html

`DM-12356 <https://jira.lsstcorp.org/browse/DM-12356>`__.

1.4.0 (2017-12-13)
==================

Removed some technical debt and drift in the Kubernetes deployment templates.

`DM-12862 <https://jira.lsstcorp.org/browse/DM-12862>`__.

1.3.0 (2017-08-08)
==================

Update ``nginx-ssl-proxy`` container for TLS security.

`DM-11502 <https://jira.lsstcorp.org/browse/DM-11502>`__.

1.2.0 (2017-02-20)
==================

Support for `LTD Dasher <https://github.com/lsst-sqre/ltd-dasher>`__.

`DM-9021 <https://jira.lsstcorp.org/browse/DM-9021>`__.

1.1.0 (2016-08-30)
==================

Support non-DM JIRA ticket types (such as ``tickets/LCR-N``) when auto-slugifying.

`DM-7439 <https://jira.lsstcorp.org/browse/DM-7439>`__.

1.0.0 (2016-08-04)
==================

Use Google Cloud SQL as the default DB with Kubernetes.

`DM-7050 <https://jira.lsstcorp.org/browse/DM-7050>`__.

0.11.0 (2016-07-28)
===================

Upload *directory redirect objects* to S3 that tell Fastly to redirect a browser from a directory path to the ``index.html`` inside.

`DM-5894 <https://jira.lsstcorp.org/browse/DM-5894>`__.

0.10.0 (2016-06-22)
===================

Fix browser caching of editions.

`DM-6111 <https://jira.lsstcorp.org/browse/DM-6111>`__.

0.9.0 (2016-05-05)
==================

Fastly API interactions.

`DM-5169 <https://jira.lsstcorp.org/browse/DM-5169>`__ and `DM-5901 <https://jira.lsstcorp.org/browse/DM-5901>`__.

0.8.0 (2016-05-05)
==================

Fastly API interactions.

`DM-5169 <https://jira.lsst.org/ <https://jira.lsstcorp.org/browse/DM-5169>`__ and `DM-5901 <https://jira.lsst.org/ <https://jira.lsstcorp.org/browse/DM-5901>`__.

0.7.0 (2016-04-14)
==================

Kubernetes deployment.

`DM-5194 <https://jira.lsst.org/ <https://jira.lsstcorp.org/browse/DM-5194>`__.

0.6.0 (2016-04-06)
==================

Fine-grained authorization for API users.

`DM-5645 <https://jira.lsst.org/ <https://jira.lsstcorp.org/browse/DM-5645>`__.

0.5.0 (2016-04-06)
==================

Fine-grained authorization for API users.

`DM-5645 <https://jira.lsst.org/ <https://jira.lsstcorp.org/browse/DM-5645>`__.

0.4.0 (2016-04-06)
==================

Initial deployment as a Docker container.

`DM-5291 <https://jira.lsst.org/ <https://jira.lsstcorp.org/browse/DM-5291>`__.

0.3.0 (2016-03-09)
==================

Minimum viable API with Edition, Build, and Product routes.

`DM-4950 <https://jira.lsst.org/ <https://jira.lsstcorp.org/browse/DM-4950>`__.

0.2.0 (2016-02-19)
==================

Interaction with AWS S3 and Route53 with product provisioning and build uploads.

`DM-4951 <https://jira.lsst.org/ <https://jira.lsstcorp.org/browse/DM-4951>`__.

0.1.0 (2016-02-10)
==================

First Flask application prototype and API design documentation.

`DM-5100 <https://jira.lsst.org/ <https://jira.lsstcorp.org/browse/DM-5100>`__.