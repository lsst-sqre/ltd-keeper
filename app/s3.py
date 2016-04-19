"""Utilities for working with S3.

In LSST the Docs, ltd-mason is responsible for uploading documentation
resources to S3. ltd-keeper deletes resources and copies builds to editions.
"""

import os
import logging
from pprint import pformat
import boto3

from .exceptions import S3Error


log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def delete_directory(bucket_name, root_path,
                     aws_access_key_id, aws_secret_access_key):
    """Delete all objects in the S3 bucket named `bucket_name` that are
    found in the `root_path` directory.

    Parameters
    ----------
    bucket_name : str
        Name of an S3 bucket.
    root_path : str
        Directory in the S3 bucket that will be deleted. The `root_path`
        should ideally end in a trailing `'/'`. E.g. `'dir/dir2/'`.
    aws_access_key_id : str
        The access key for your AWS account. Also set `aws_secret_access_key`.
    aws_secret_access_key : str
        The secret key for your AWS account.

    Raises
    ------
    app.exceptions.S3Error
        Thrown by any unexpected faults from the S3 API.
    """
    session = boto3.session.Session(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key)
    s3 = session.resource('s3')
    bucket = s3.Bucket(bucket_name)

    # Normalize directory path for searching patch prefixes of objects
    if not root_path.endswith('/'):
        root_path += '/'

    key_objects = [{'Key': obj.key}
                   for obj in bucket.objects.filter(Prefix=root_path)]
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


def copy_directory(bucket_name, src_path, dest_path,
                   aws_access_key_id, aws_secret_access_key):
    """Copy objects from one directory in a bucket to another directory in
    the same bucket.

    Parameters
    ----------
    bucket_name : str
        Name of an S3 bucket.
    src_path : str
        Source directory in the S3 bucket. The `src_path` should ideally end
        in a trailing `'/'`. E.g. `'dir/dir2/'`.
    dest_path : str
        Destination directory in the S3 bucket. The `dest_path` should ideally
        end in a trailing `'/'`. E.g. `'dir/dir2/'`. The destination path
        cannot contain the source path.
    aws_profile : str, optional
        Name of an AWS credential profile in :file:`~/.aws/credentials`
        that has access to the needed Route 53 hosted zone.

    Raises
    ------
    app.exceptions.S3Error
        Thrown by any unexpected faults from the S3 API.
    """
    if not src_path.endswith('/'):
        src_path += '/'
    if not dest_path.endswith('/'):
        dest_path += '/'

    # Ensure the src_path and dest_path don't contain each other
    common_prefix = os.path.commonprefix([src_path, dest_path])
    assert common_prefix != src_path
    assert common_prefix != dest_path

    # Delete any existing objects in the destination
    delete_directory(bucket_name, dest_path,
                     aws_access_key_id, aws_secret_access_key)

    session = boto3.session.Session(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key)
    s3 = session.resource('s3')
    bucket = s3.Bucket(bucket_name)

    # Copy each object from source to destination
    for src_obj in bucket.objects.filter(Prefix=src_path):
        src_rel_path = os.path.relpath(src_obj.key, start=src_path)
        dest_key_path = os.path.join(dest_path, src_rel_path)
        s3.meta.client.copy_object(
            Bucket=bucket_name,
            Key=dest_key_path,
            CopySource={'Bucket': bucket_name, 'Key': src_obj.key},
            MetadataDirective='COPY',
            ACL='public-read')
