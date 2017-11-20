#######################
Editions - `/editions/`
#######################

An Edition is a publication of a :doc:`Product <products>`\ ’s documentation.
Editions allow products to have multiple versions of documentation published at once, from separate URLs.
For example, the 'latest' documentation might be published to ``docs.project.org``, but documentation for the tagged 'v1' release might be published to ``docs.project.org/v/v1``.

Editions are merely pointers to a :doc:`Build <builds>`; an Edition is updated by pointing to a newer :doc:`Build <builds>` (see :http:patch:`/editions/(int:id)`).

Methods
=======

- :http:get:`/editions/(int:id)` --- show a single Edition.

- :http:patch:`/editions/(int:id)` --- update an Edition.

- :http:delete:`/editions/(int:id)` --- deprecate an Edition.

*See also:*

- :http:post:`/products/(slug)/editions/` --- create a new Edition for a Product.

- :http:get:`/products/(slug)/editions/` --- list all Edition for a Product.

- :http:get:`/products/(slug)/editions/` --- list all Edition for a Product.

Reference
=========

.. autoflask:: app:create_app(profile='development')
   :endpoints: api.get_edition, api.edit_edition, api.deprecate_edition
