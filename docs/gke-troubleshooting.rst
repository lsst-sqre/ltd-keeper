############################################
Troubleshooting Kubernetes Deployment Issues
############################################

This page captures known operational issues seen in the Kubernetes deployment and work-arounds.

Error syncing pod, skipping: Could not attach GCE PD "keeper-disk". Timeout waiting for mount paths to be created.
==================================================================================================================

This can happen when the node that is using the persistent disk ``keeper-disk`` dies and is restarted.
It may not have re-attached properly, preventing the Keeper deployment's replication controller from re-launching the keeper pod.

A work-around is to manually detach the persistent disk:

.. code-block:: bash

   gcloud compute instances detach-disk {{node name}} --disk keeper-disk

This should be fixed in Kubernetes 1.3.
See `Kubernetes GitHub Issue 14642 <https://github.com/kubernetes/kubernetes/issues/14642>`_.
