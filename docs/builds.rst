###################
Builds - `/builds/`
###################

In LTD Keeper, a Build is created every time a Sphinx repository is compiled and uploaded to S3.
LTD Keeper doesn't touch objects in S3 directly; LTD Mason uploads documentation sites to S3 and then registers the build with  LTD Keeper.

New builds added using the :http:post:`/v1/products/(slug)/builds/` method.
The methods listed on this page allow you to list maintain builds (such as showing or deprecating them).

Methods
=======

- :http:post:`/v1/builds/(int:id)/uploaded` --- register a build upload.

- :http:get:`/v1/builds/(int:id)` --- show a build.

- :http:delete:`/v1/builds/(int:id)` --- deprecate a build.

*See also:*

- :http:post:`/v1/products/(slug)/builds/` --- create a new build for a product.

- :http:get:`/v1/products/(slug)/builds/` --- list all builds for a product.

Reference
=========

.. autoflask:: app:create_app(config_name='development')
   :endpoints: api.get_build, api.register_build_upload, api.deprecate_build
