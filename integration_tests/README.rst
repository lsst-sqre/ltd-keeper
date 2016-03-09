#################
Integration Tests
#################

We use integration tests to test code functionality against real-world resources, such as AWS.

Configuration
=============

These tests assume you have credentials for the lsst-sqre AWS account, and that those credentials are in a :file:`~/.aws/credentials` file under a ``ltd-dev`` profile.
See http://boto3.readthedocs.org/en/latest/guide/quickstart.html#configuration.

These tests use the following mock resources:

- ``lsst-the-docs-test`` bucket in S3.
- ``ltdtest.local.`` hosted zone in Route 53.

Available Tests
===============

- ``integration_tests/test_route53.py``
- ``integration_tests/test_s3_deletion.py``
