#######################################################
Updating the Production Keeper Deployment on Kubernetes
#######################################################

Kubernetes makes it easy to update LTD Keeper in production with minimal downtime (or no downtime if several Keeper pods are being load balanced).

Note that this procedure could be considered immature.
Ideally we would have a staging cluster to run end-to-end tests on upgrade candidate, and only then introduce the upgraded application into production with the canary pattern.
The deployment procedure described here can still be rolled-back quickly if a fault is detected.

Procedure
=========

1. Keeper should be pushed to GitHub and pass all tests on Travis CI.

2. Formally make a Git release by tagging it:

   .. code-block:: bash

      git tag -s X.Y.Z -m "X.Y.Z"
      git push --tags

   Travis CI pushes a new Docker image to Docker Hub.
   See :doc:`docker-image`.

3. In :file:`keeper-deployment.yaml`, :file:`keeper-deployment.yaml`, and :file:`keeper-mgmt-pod.yaml` update the name of the ``uwsgi`` container's ``image`` to the new Docker image: ``lsstsqre/ltd-keeper:X.Y.Z``.

4. Apply the new deployment configuration:

   .. code-block:: bash

      kubectl apply -f keeper-deployment.yaml
      kubectl apply -f keeper-worker-deployment.yaml
   
   To follow the upgrade, use these commands:

   .. code-block:: bash

      kubectl describe deployment keeper-deployment
      kubectl describe deployment keeper-worker-deployment
      kubectl get pods
