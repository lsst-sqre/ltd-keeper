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
                   aws_access_key_id, aws_secret_access_key,
                   surrogate_key=None, cache_control=None,
                   surrogate_control=None):
    """Copy objects from one directory in a bucket to another directory in
    the same bucket.

    Object metadata is preserved while copying, with the following exceptions:

    - If a new surrogate key is provided it will replace the original one.
    - If cache_control and surrogate_control values are provided they
      will replace the old one.

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
    aws_access_key_id : str
        The access key for your AWS account. Also set `aws_secret_access_key`.
    aws_secret_access_key : str
        The secret key for your AWS account.
    surrogate_key : str, optional
        The surrogate key to insert in the header of all objects in the
        ``x-amz-meta-surrogate-key`` field. This key is used to purge
        builds from the Fastly CDN when Editions change.
        If `None` then no header will be set.
        If the object already has a ``x-amz-meta-surrogate-key`` header then
        it will be replaced.
    cache_control : str, optional
        This sets (and overrides) the ``Cache-Control`` header on the copied
        files. The ``Cache-Control`` header specifically dictates how content
        is cached by the browser (if ``surrogate_control`` is also set).
    surrogate_control : str, optional
        This sets (and overrides) the ``x-amz-meta-surrogate-control`` header
        on the copied files. The ``Surrogate-Control``
        or ``x-amz-meta-surrogate-control`` header is used in priority by
        Fastly to givern it's caching. This caching policy is *not* passed
        to the browser.

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

        # the src_obj (ObjectSummary) doesn't include headers afaik
        head = s3.meta.client.head_object(Bucket=bucket_name,
                                          Key=src_obj.key)
        metadata = head['Metadata']
        content_type = head['ContentType']

        # try to use original Cache-Control header if new one is not set
        if cache_control is None and 'CacheControl' in head:
            cache_control = head['CacheControl']

        if surrogate_control is not None:
            metadata['surrogate-control'] = surrogate_control

        if surrogate_key is not None:
            metadata['surrogate-key'] = surrogate_key

        s3.meta.client.copy_object(
            Bucket=bucket_name,
            Key=dest_key_path,
            CopySource={'Bucket': bucket_name, 'Key': src_obj.key},
            MetadataDirective='REPLACE',
            Metadata=metadata,
            ACL='public-read',
            CacheControl=cache_control,
            ContentType=content_type)
