##########
Change log
##########

1.12.0 (2017-07-10)
===================

- Update to Python 3.6.6 (in Docker base image and Travis).
- Update boto to 1.7.54 (for Python 3.6.6 compatibility).
- Update Celery to 4.2.0 (to fix a compatibility issue with Kombu 4.2's release).

1.11.0 (2018-07-09)
===================

This release improves and expands the system of edition tracking modes.

There are three new tracking modes:

- ``eups_major_release`` tracks an EUPS major release tag (``vX_Y``) and its Git variant (``X.Y``).
- ``eups_weekly_release`` tracks an EUPS weekly release tag (``w_YYYY_WW``) and its Git variant (``w.YYYY.WW``).
- ``eups_daily_release`` tracks an EUPS daily release tag (``d_YYYY_MM_DD``) and its Git variant (``d.YYYY.MM.DD``).

In addition, the code for determining whether an edition should rebuild or not given the tracking mode has been refactored out of the ``Edition.should_rebuild`` model method and into a new ``keeper.editiontracking`` subpackage.
Each tracking mode is now built around a uniform interface.

`DM-15016 <https://jira.lsstcorp.org/browse/DM-15016>`__.

1.10.0 (2018-06-12)
===================

Both ``.`` and ``_`` characters can now appear in edition slugs.
Previously these characters were automatically converted to ``-`` characters in edition names, but this prevented editions from being named after semantic version tags or EUPS tags.

`DM-14772 <https://jira.lsstcorp.org/browse/DM-14772>`__.

1.9.0 (2018-05-03)
==================

This release includes the celery task queuing system and major internal updates to the application structure and dependencies.

`DM-14122 <https://jira.lsstcorp.org/browse/DM-14122>`__.

API updates
-----------

- Endpoints that launch asynchronous queue tasks now provide a ``queue_url`` field.
  This is a URL to an endpoint that provides status information on the queued task.
  For example, after ``PATCH``\ ing an edition with a new build, you can watch the ``queue_url`` to see when the rebuild is complete.
  The ``queue_url``\ s are provided by the new ``GET /queue/(id)`` endpoint.

- We don't yet provide a way to query the queue in general --- you can only get URLs by being the user that triggered the task.

- Endpoints, especially ``PATCH /editions/(id)``, should no longer timeout (500 error) for large documentation projects.

- The ``/editions/(id)`` resource includes a new ``pending_rebuild`` field.
  This field acts as a semaphore and is set to ``true`` if there is a pending rebuild task.
  You can't ``PATCH`` the edition's ``build_url`` when ``pending_rebuild`` is ``true``.
  If necessary, an operator can ``PATCH`` ``pending_rebuild`` to ``false`` if the Celery task that rebuilds the edition failed.

Deployment updates
------------------

- New deployment: ``keeper-redis``.
  This deployment consists of a single Redis container (official ``redis:4-alpine`` image).
  There is no persistent storage or high-availability at this time (this was judged a fair trade off since the Celery queue is inherently transient).
- New service: ``keeper-redis``.
  This service fronts the ``keeper-redis`` deployment.
- New deployment: ``keeper-worker-deployment``.
  This deployment mirrors ``keeper-deployment``, except that the run ``command`` starts a Celery worker for the LTD Keeper application.
  This deployment can be scaled up to provide additional workers.
  The ``keeper-worker-deployment`` is *not* fronted by a service since the Celery workers pull tasks from ``keeper-redis``.

Internal updates
----------------

- Dependency updates:

  - Flask 0.12.2
  - Requests 2.18.4
  - uwsgi 2.0.17
  - Flask-SQLAlchemy 2.3.2
  - PyMySQL 0.8.0
  - Flask-Migrate 2.1.1

- Switched from Flask-Script to ``flask.cli``.
  The Makefile now fronts most of the Flask commands for convience during development.
  Run ``make help`` to learn more.

- Application architecture improvements:

  - Moved the Flask application factory out of ``__init__.py`` to ``keeper.appfactory``.
  - Moved the ``get_auth_token`` route to the ``api`` blueprint.
  - Moved DB connection object to ``keeper.models.db``.

- Add ``Product.from_url()`` and ``Edition.from_url()`` methods for consistency with ``Build.from_url``.

- Logging updates:

  - Now we specifically set up the ``keeper`` logger instead of the root logger.
    This keeps things manageable when turning on debug-level logging.

  - New app configuration for logging level.
    Debug-level logging is used in the development and testing profiles, while info-level logging is used in production.

- New celery app factory in ``keeper.celery``.

- New Celery task queuing infrastructure in ``keeper.taskrunner``.
  In a request context, application code can add an asynchronous task by calling ``append_task_to_chain()`` with a Celery task signature.
  These task signatures are persisted, within the request context, in ``flask.g.tasks``.
  Just before a route handler returns it should call ``launch_task_chain()``, which launches the task chain asynchronously.
  The advantage of this whole-context chain is that it orders asynchronous tasks: editions are rebuilt before the dashboard is created.
  If a task is known to be fully independent of other tasks it could just be launched immediately.

- New Celery tasks:

  - ``keeper.tasks.editionrebuild.rebuild_edition()``: copies a build on S3 onto the edition.
  - ``keeper.tasks.dashboardbuild.build_dashboard()``: triggers LTD Dasher.

- Replace ``Edition.rebuild()`` with ``Edition.set_pending_rebuild`` to use the new ``rebuild_edition`` task.

1.8.0 (2017-12-13)
==================

Adds logging with `structlog <http://www.structlog.org/en/stable/>`__.
Structlog is configured to generate key-value log strings in test/development and JSON-formatted strings in production.
The ``@log_route`` decorator creates a new logger and binds metadata about a request, such as a unique request ID, method and path.
It also logs the response latency and status when the route returns.
The auth decorators bind the username once the user is known.

`DM-12974 <https://jira.lsstcorp.org/browse/DM-12974>`__.

1.7.0 (2017-12-13)
==================

In this version we've dropped the ``nginx-ssl-proxy`` pod that we've used thus far and adopted the standard Kubernetes Ingress resources for TLS termination instead.
This means that the Keeper service is now a NodePort-type service.
The advantage of using Ingress is that we can rely on Google to maintain that resource and ensure that the TLS-terminating proxy is updated with new security patches.

`DM-12923 <https://jira.lsstcorp.org/browse/DM-12923>`__.

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
