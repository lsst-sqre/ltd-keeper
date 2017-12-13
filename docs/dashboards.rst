##########################
Dashboards - `/dashboards`
##########################

The ``/dashboards`` API allows you to update dashboards for products in bulk.

Dashboards are normally rebuilt whenever a new build or edition are created or updated.
But if the dashboard design changes, it is useful to trigger a rebuild of all dashboards.

Dashboards are created by the `LTD Dasher <https://github.com/lsst-sqre/ltd-dasher>`_ microservice.

Method summary
==============

- :http:post:`/dashboards` --- rebuild all dashboards.

Reference
=========

.. autoflask:: keeper:create_app(profile='development')
   :endpoints: api.rebuild_all_dashboards
