#######################
Editions - `/editions/`
#######################

An Edition is a publication of a :doc:`Product <products>`\ ’s documentation.
Editions allow products to have multiple versions of documentation published at once, from separate URLs.
For example, the 'latest' documentation might be published to ``docs.project.org``, but documentation for the tagged 'v1' release might be published to ``docs.project.org/v/v1``.

Editions are merely pointers to a :doc:`Build <builds>`; an Edition is updated by pointing to a newer :doc:`Build <builds>` (see :http:patch:`/editions/(int:id)`).

Tracking modes
==============

Editions track :doc:`Builds <builds>`.
This means that when a new :doc:`Build <builds>` is uploaded, any Edition for that :doc:`Product <products>` that tracks that *kind* of Build will be updated.
An Edition's tracking mode is given with the ``mode`` field, and can either be set initially (:http:post:`/products/(slug)/editions/`) or updated on an existing Edition (:http:patch:`/editions/(int:id)`).
There are two tracking modes, currently:

============ =================================
mode field   Tracking behavior
============ =================================
``git_refs`` Git branches and tags
``lsst_doc`` Latest LSST document version tags
============ =================================

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

LSST document mode (``lsst_doc``)
---------------------------------

This mode makes the Edition track the :doc:`Build <builds>` with the most recent LSST document semantic version tag.
LSST document semantic version tags are formatted as ``v<Major>.<Minor>``.

Enable this mode by setting the Edition's ``mode`` field to ``lsst_doc``.

Note that until the first :doc:`Build <builds>` with a semantic version tag is published, an Edition with this mode will track the ``master`` Git ref.

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

.. autoflask:: app:create_app(profile='development')
   :endpoints: api.get_edition, api.edit_edition, api.deprecate_edition
