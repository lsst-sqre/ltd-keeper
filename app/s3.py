"""Utilities for working with S3.

In LSST the Docs, ltd-mason is responsible for uploading documentation
resources to S3. ltd-keeper only really needs to delete resources.
"""

import logging
from pprint import pformat
import boto3

from .exceptions import S3Error


log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def delete_directory(bucket_name, root_path, aws_profile='default'):
    """Delete all objects in the S3 bucket named `bucket_name` that are
    found in the `root_path` directory.

    Parameters
    ----------
    bucket_name : str
        Name of an S3 bucket.
    root_path : str
        Directory in the S3 bucket that will be deleted. The `root_path`
        should ideally end in a trailing `'/'`. E.g. `'dir/dir2/'`.
    aws_profile : str, optional
        Name of an AWS credential profile in :file:`~/.aws/credentials`
        that has access to the needed Route 53 hosted zone.

    Raises
    ------
    app.exceptions.S3Error
        Thrown by any unexpected faults from the S3 API.
    """
    session = boto3.session.Session(profile_name=aws_profile)
    s3 = session.resource('s3')
    bucket = s3.Bucket(bucket_name)

    # Normalize directory path for searching patch prefixes of objects
    if not root_path.endswith('/'):
        root_path += '/'

    key_objects = [{'Key': obj.key}
                   for obj in bucket.objects.filter(Prefix=root_path)]
    assert len(key_objects) > 0
    if len(key_objects) == 0:
        log.info('No objects deleted from bucket {0}:{1}'.format(
            bucket_name, root_path))
        return
    delete_keys = {'Objects': []}
    delete_keys['Objects'] = key_objects
    log.info('Deleting {0:d} objects from bucket {1}:{2}'.format(
        len(key_objects), bucket_name, root_path))
    # based on http://stackoverflow.com/a/34888103
    r = s3.meta.client.delete_objects(Bucket=bucket.name,
                                      Delete=delete_keys)
    log.info(pformat(r))
    status_code = r['ResponseMetadata']['HTTPStatusCode']
    if status_code >= 300:
        msg = 'S3 could not delete {0} (status {1:d})'.format(
            root_path, status_code)
        log.error(msg)
        raise S3Error(msg)
