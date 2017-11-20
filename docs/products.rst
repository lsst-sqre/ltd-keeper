######################
Products - `/products`
######################

The ``/products/`` API allows you to list Products, create new Products, and update Products (including adding new :doc:`Builds <builds>` and :doc:`Editions <editions>`).

In LTD Keeper, a Product is the root entity associated with a documentation project.
Generally, a single Sphinx documentation repository maps to a Product.
LTD Keeper can host documentation for several products.

The actual documentation associated with a Product is manifested by :doc:`Builds <builds>`.
In turn, :doc:`Builds <builds>` are the source of :doc:`Editions <editions>`, which are published versions of the Product's documentation.

Method Summary
==============

- :http:get:`/products/` --- list all documentation products.

- :http:get:`/products/(slug)` --- show a single product.

- :http:post:`/products/` --- create a new product.

- :http:patch:`/products/(slug)` --- update a product's metadata.

- :http:post:`/products/(slug)/builds/` --- create a new build for a product.

- :http:get:`/products/(slug)/builds/` --- list all builds for a product.

- :http:post:`/products/(slug)/editions/` --- create a new edition for a product.

- :http:get:`/products/(slug)/editions/` --- list all edition for a product.

- :http:get:`/products/(slug)/editions/` --- list all edition for a product.

- :http:post:`/products/(slug)/dashboard` --- manually rebuild the dashboards for a product.

*See also:*

- :doc:`/builds/ <builds>`

- :doc:`/editions/ <editions>`

Reference
=========

.. autoflask:: app:create_app(profile='development')
   :endpoints: api.get_products, api.get_product, api.new_product, api.edit_product, api.new_build, api.get_product_builds, api.new_edition, api.get_product_editions, api.rebuild_product_dashboard
