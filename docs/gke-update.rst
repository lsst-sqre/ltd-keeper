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

2. Build a new Docker image and push to Docker Hub according to procedure on :doc:`docker-image`.
   Give the image a unique tag; we haven't adopted a format yet, but ``:YYYYMMDD-N`` works.

3. Update the :file:`keeper-deployment.yaml` and update the name of the ``uwsgi`` container's ``image`` to the new Docker image.

4. Apply the new deployment configuration:

   .. code-block:: bash

      kubectl apply -f keeper-deployment.yaml
   
   To follow the upgrade, use these commands:

   .. code-block:: bash

      kubectl describe deployment keeper-deployment
      kubectl get pods
