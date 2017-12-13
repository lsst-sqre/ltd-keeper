############
Introduction
############

LTD Keeper provides a simple RESTFul API for both administering and browsing documentation resources.

Users and authentication
========================

LTD Keeper requires authentication for POST/PUT/PATCH/DELETE operations, but GET requests can be anonymous.

Authenticated API users have a username and password, but a token must be generated for requests.
See the :doc:`Authentication <auth>` page for information about obtaining a token.

Note that there is no public API for registering new users.

Versioning
==========

The LTD Keeper API is in beta and can be changed without notice.
In the future, we may elect to version the API through the ``Accept`` header.

Content types
=============

All data in the bodies of requests and responses is ``application/json``.

Resources
=========

LTD Keeper's API expresses three basic resource types:

:doc:`Products <products>`
   A Product represents a software project or a writing project.
   Generally speaking, a Product maps to a GitHub repository or an Eups meta-product.

:doc:`Builds <builds>`
   An instance of a Product's documentation is a Build.
   Builds are immutable; updating a Product's documentation means creating/uploading a new Build.

:doc:`Editions <editions>`
   Editions represent stable URLs where a reader can expect to find different *versions* of a Product's documentation.
   Examples of Editions might be 'latest' that tracks documentation for the master branch of a Product, or a 'v1' Edition for that released version of a product.
   Although Editions have stable URLs, they can be updated by pointing to a different Build.
