#######################
Editions - `/editions/`
#######################

An Edition is a publication of a Product's documentation.
Editions allow products to have multiple versions of documentation published at once, from separate URLs.
For example, the 'latest' documentation might be published to ``docs.project.org``, but documentation for the tagged 'v1' might be published to ``v1.docs.project.org``.

Editions are merely pointers to a Build; an Edition is updated by pointing to a newer build (see :http:patch:`/editions/(int:id)`).

Methods
=======

- :http:get:`/editions/(int:id)` --- show a single edition.

- :http:patch:`/editions/(int:id)` --- update an edition.

- :http:delete:`/editions/(int:id)` --- deprecate an edition.



*See also:*

- :doc:`/products/ <products>` for creating a new edition associated with a product.

Reference
=========

.. autoflask:: app:create_app(config_name='development')
   :endpoints: api.get_edition, api.edit_edition, api.deprecate_edition
