###################
Builds - `/builds/`
###################

In LTD Keeper, a Build is created every time a Sphinx repository is compiled and uploaded to S3.
LTD Keeper doesn't touch objects in S3 directly; LTD Mason uploads documentation sites to S3 and then registers the build with  LTD Keeper.

New builds added using the :http:post:`/products/(slug)/builds/` method.
The other methods listed on this page allow you to list and maintain Builds (such as showing or deprecating them).

Methods
=======

- :http:patch:`/builds/(int:id)` --- modify a build record, usually to register a build upload.

- :http:get:`/builds/(int:id)` --- show a build.

- :http:delete:`/builds/(int:id)` --- deprecate a build.

*See also:*

- :http:post:`/products/(slug)/builds/` --- create a new build for a :doc:`Product <products>`.

- :http:get:`/products/(slug)/builds/` --- list all builds for a :doc:`Product <products>`.

Reference
=========

.. autoflask:: keeper:flask_app
   :endpoints: api.get_build, api.patch_build, api.deprecate_build
