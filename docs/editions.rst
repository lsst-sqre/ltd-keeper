#######################
Editions - `/editions/`
#######################

An Edition is a publication of a :doc:`Product <products>`\ ’s documentation.
Editions allow products to have multiple versions of documentation published at once, from separate URLs.
For example, the 'latest' documentation might be published to ``docs.project.org``, but documentation for the tagged 'v1' release might be published to ``docs.project.org/v/v1``.

Editions are merely pointers to a :doc:`Build <builds>`; an Edition is updated by pointing to a newer :doc:`Build <builds>` (see :http:patch:`/editions/(int:id)`).

.. _edition-tracking-modes:

Tracking modes
==============

Editions track :doc:`Builds <builds>`.
This means that when a new :doc:`Build <builds>` is uploaded, any Edition for that :doc:`Product <products>` that tracks that *kind* of Build will be updated.
An Edition's tracking mode is given with the ``mode`` field, and can either be set initially (:http:post:`/products/(slug)/editions/`) or updated on an existing Edition (:http:patch:`/editions/(int:id)`).

These are the available tracking modes:

.. list-table::
   :header-rows: 1

   * - ``mode`` field
     - Tracking behavior

   * - :ref:`git_refs <git_refs-tracking-mode>`
     - Git branches and tags

   * - :ref:`lsst_doc <lsst_doc-tracking-mode>`
     - Latest LSST document version tags

   * - :ref:`eups_major_release <eups_major_release-tracking-mode>`
     - Latest EUPS major release tags

   * - :ref:`eups_weekly_release <eups_weekly_release-tracking-mode>`
     - Latest EUPS weekly release tags

   * - :ref:`eups_daily_release <eups_daily_release-tracking-mode>`
     - Latest EUPS daily release tags

.. _git_refs-tracking-mode:

Git reference mode (``git_refs``, default)
------------------------------------------

This mode tracks Builds with a specific Git ref (branch name or tag).

Enable this mode by setting the Edition's ``mode`` field to ``git_refs``.
Then set the ``tracked_refs`` field with array of Git ref strings that determine the value of ``git_refs`` a :doc:`Build <builds>` needs to be published as the Edition.

As an example, an Edition has these fields:

.. code-block:: json

   {
     "mode": "git_refs",
     "tracked_refs": ["master"]
   }

Then a :doc:`Build <builds>` with ``{"git_refs": ["master"]}`` will be published by the Edition.

.. _lsst_doc-tracking-mode:

LSST document mode (``lsst_doc``)
---------------------------------

This mode makes the Edition track the :doc:`Build <builds>` with the most recent LSST document semantic version tag.
LSST document semantic version tags are formatted as ``v<Major>.<Minor>``.

Enable this mode by setting the Edition's ``mode`` field to ``lsst_doc``.

Note that until the first :doc:`Build <builds>` with a semantic version tag is published, an Edition with this mode will track the ``master`` Git ref.

.. _eups_major_release-tracking-mode:

EUPS major release tag (``eups_major_release``)
-----------------------------------------------

This mode makes the edition track the :doc:`Build <builds>` with the most recent EUPS major release tag.

EUPS major release tags have two forms that are both treated interchangeably:

- EUPS tag: ``vX_Y`` (as in ``v15_0``).
- Git tag: ``X_Y`` (as in ``15.0``).

Enable this mode by setting the Edition's ``mode`` field to ``eups_major_release``.

.. _eups_weekly_release-tracking-mode:

EUPS weekly release tag (``eups_weekly_release``)
-------------------------------------------------

This mode makes the edition track the :doc:`Build <builds>` with the most recent EUPS weekly release tag.

EUPS weekly release tags have two forms that are both treated interchangeably:

- EUPS tag: ``w_YYYY_WW`` (as in ``w_2018_01``).
- Git tag: ``w.YYYY.WW`` (as in ``w.2018.01``).

Enable this mode by setting the Edition's ``mode`` field to ``eups_weekly_release``.

.. _eups_daily_release-tracking-mode:

EUPS daily release tag (``eups_daily_release``)
-----------------------------------------------

This mode makes the edition track the :doc:`Build <builds>` with the most recent EUPS daily release tag.

EUPS daily release tags have two forms that are both treated interchangeably:

- EUPS tag: ``d_YYYY_MM_DD`` (as in ``d_2018_01_01``).
- Git tag: ``d.YYYY.MM.DD`` (as in ``d.2018.01.01``).

Enable this mode by setting the Edition's ``mode`` field to ``eups_daily_release``.

Methods
=======

- :http:get:`/editions/(int:id)` --- show a single Edition.

- :http:patch:`/editions/(int:id)` --- update an Edition.

- :http:delete:`/editions/(int:id)` --- deprecate an Edition.

*See also:*

- :http:post:`/products/(slug)/editions/` --- create a new Edition for a Product.

- :http:get:`/products/(slug)/editions/` --- list all Editions for a Product.

Reference
=========

.. autoflask:: keeper:flask_app
   :endpoints: api.get_edition, api.edit_edition, api.deprecate_edition
