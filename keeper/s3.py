"""Utilities for working with S3.

In LSST the Docs, ltd-mason is responsible for uploading documentation
resources to S3. ltd-keeper deletes resources and copies builds to editions.
"""

from __future__ import annotations

import logging
import os
from copy import deepcopy
from typing import (
    TYPE_CHECKING,
    Any,
    Collection,
    Dict,
    List,
    Optional,
    Sequence,
    Union,
)

import boto3
import botocore.exceptions
from botocore.client import Config

from keeper.exceptions import S3Error

if TYPE_CHECKING:
    import botocore.client.S3

__all__ = (
    "open_aws_session",
    "open_s3_resource",
    "delete_directory",
    "copy_directory",
    "presign_post_url_for_prefix",
    "presign_post_url_for_directory_object",
    "format_bucket_prefix",
)


def open_aws_session(
    *, key_id: str, access_key: str, aws_region: str
) -> boto3.session.Session:
    """Create a boto3 AWS session that can be reused by multiple requests.

    Parameters
    ----------
    aws_access_key_id : str
        The access key for your AWS account. Also set `aws_secret_access_key`.
    aws_secret_access_key : str
        The secret key for your AWS account.
    aws_region : str
        The AWS region (``us-east-1`` or ``ca-central-1``).
    """
    return boto3.session.Session(
        aws_access_key_id=key_id,
        aws_secret_access_key=access_key,
        region_name=aws_region,
    )


def open_s3_resource(
    *, key_id: str, access_key: str, aws_region: str
) -> boto3.resources.base.ServiceResource:
    session = open_aws_session(
        key_id=key_id, access_key=access_key, aws_region=aws_region
    )
    s3 = session.resource("s3", config=Config(signature_version="s3v4"))
    return s3


def delete_directory(
    *,
    s3: boto3.resources.base.ServiceResource,
    bucket_name: str,
    root_path: str,
) -> None:
    """Delete all objects in the S3 bucket named `bucket_name` that are
    found in the `root_path` directory.

    Parameters
    ----------
    s3
        The S3 service.
    bucket_name : str
        Name of an S3 bucket.
    root_path : str
        Directory in the S3 bucket that will be deleted.

    Raises
    ------
    app.exceptions.S3Error
        Thrown by any unexpected faults from the S3 API.
    """
    log = logging.getLogger(__name__)

    s3_client = s3.meta.client

    # Normalize directory path for searching patch prefixes of objects
    if not root_path.endswith("/"):
        root_path.rstrip("/")

    paginator = s3_client.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket_name, Prefix=root_path)

    keys: Dict[str, List[Dict[str, str]]] = dict(Objects=[])
    for item in pages.search("Contents"):
        try:
            keys["Objects"].append({"Key": item["Key"]})
        except TypeError:  # item is none; nothing to delete
            continue
        # Delete immediately when 1000 objects are listed
        # the delete_objects method can only take a maximum of 1000 keys
        if len(keys["Objects"]) >= 1000:
            try:
                s3_client.delete_objects(Bucket=bucket_name, Delete=keys)
            except Exception:
                message = "Error deleting objects from %r" % root_path
                log.exception("Error deleting objects from %r", root_path)
                raise S3Error(message)
            keys = dict(Objects=[])

    # Delete remaining keys
    if len(keys["Objects"]) > 0:
        try:
            s3_client.delete_objects(Bucket=bucket_name, Delete=keys)
        except Exception:
            message = "Error deleting objects from %r" % root_path
            log.exception(message)
            raise S3Error(message)


def copy_directory(
    *,
    s3: boto3.resources.base.ServiceResource,
    bucket_name: str,
    src_path: str,
    dest_path: str,
    surrogate_key: Optional[str] = None,
    cache_control: Optional[str] = None,
    surrogate_control: Optional[str] = None,
    create_directory_redirect_object: bool = True,
    use_public_read_acl: bool = False,
) -> None:
    """Copy objects from one directory in a bucket to another directory in
    the same bucket.

    Object metadata is preserved while copying, with the following exceptions:

    - If a new surrogate key is provided it will replace the original one.
    - If cache_control and surrogate_control values are provided they
      will replace the old one.

    Parameters
    ----------
    s3
        The S3 resource.
    bucket_name : str
        Name of an S3 bucket.
    src_path : str
        Source directory in the S3 bucket. The `src_path` should ideally end
        in a trailing `'/'`. E.g. `'dir/dir2/'`.
    dest_path : str
        Destination directory in the S3 bucket. The `dest_path` should ideally
        end in a trailing `'/'`. E.g. `'dir/dir2/'`. The destination path
        cannot contain the source path.
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
    create_directory_redirect_object : bool, optional
        Create a directory redirect object for the root directory. The
        directory redirect object is an empty S3 object named after the
        directory (without a trailing slash) that contains a
        ``x-amz-meta-dir-redirect=true`` HTTP header. LSST the Docs' Fastly
        VCL is configured to redirect requests for a directory path to the
        directory's ``index.html`` (known as *courtesy redirects*).
    use_public_read_acl : bool
        If True, apply the ``public-read`` ACL to bucket objects.

    Raises
    ------
    app.exceptions.S3Error
        Thrown by any unexpected faults from the S3 API.
    """
    s3_client = s3.meta.client

    if not src_path.endswith("/"):
        src_path += "/"
    if not dest_path.endswith("/"):
        dest_path += "/"

    # Ensure the src_path and dest_path don't contain each other
    common_prefix = os.path.commonprefix([src_path, dest_path])
    assert common_prefix != src_path
    assert common_prefix != dest_path

    # Delete any existing objects in the destination
    delete_directory(s3=s3, bucket_name=bucket_name, root_path=dest_path)

    bucket = s3.Bucket(bucket_name)

    # Copy each object from source to destination
    for src_obj in bucket.objects.filter(Prefix=src_path):
        print(f"Copying {src_obj.key}")
        src_rel_path = os.path.relpath(src_obj.key, start=src_path)
        dest_key_path = os.path.join(dest_path, src_rel_path)

        # the src_obj (ObjectSummary) doesn't include headers afaik
        head = s3_client.head_object(Bucket=bucket_name, Key=src_obj.key)
        metadata = head["Metadata"]
        content_type = head["ContentType"]

        # try to use original Cache-Control header if new one is not set
        if cache_control is None and "CacheControl" in head:
            cache_control = head["CacheControl"]

        if surrogate_control is not None:
            metadata["surrogate-control"] = surrogate_control

        if surrogate_key is not None:
            metadata["surrogate-key"] = surrogate_key

        copy_kwargs = {
            "Bucket": bucket_name,
            "Key": dest_key_path,
            "CopySource": {"Bucket": bucket_name, "Key": src_obj.key},
            "MetadataDirective": "REPLACE",
            "Metadata": metadata,
            "CacheControl": cache_control,
            "ContentType": content_type,
        }
        if use_public_read_acl:
            copy_kwargs["ACL"] = "public-read"
        s3_client.copy_object(**copy_kwargs)

    if create_directory_redirect_object:
        dest_dirname = dest_path.rstrip("/")
        metadata = {"dir-redirect": "true"}
        upload_dir_redirect_object(
            bucket_dir_path=dest_dirname,
            bucket=bucket,
            metadata=metadata,
            acl="public-read" if use_public_read_acl else None,
            cache_control=cache_control,
        )


def upload_object(
    *,
    bucket_path: str,
    bucket: Any,
    content: Union[str, bytes] = "",
    metadata: Optional[Dict[str, str]] = None,
    acl: Optional[str] = None,
    cache_control: Optional[str] = None,
    content_type: Optional[str] = None,
) -> None:
    """Upload an arbitrary object to an S3 bucket.

    Parameters
    ----------
    bucket_path : `str`
        Destination path (also known as the key name) of the file in the
        S3 bucket.
    content : `str` or `bytes`, optional
        Object content.
    bucket : boto3 Bucket instance
        S3 bucket.
    metadata : `dict`, optional
        Header metadata values. These keys will appear in headers as
        ``x-amz-meta-*``.
    acl : `str`, optional
        A pre-canned access control list. See
        https://docs.aws.amazon.com/AmazonS3/latest/dev/acl-overview.html#canned-acl
        Default is `None`, meaning that no ACL is applied to the object.
    cache_control : `str`, optional
        The cache-control header value. For example, ``'max-age=31536000'``.
    content_type : `str`, optional
        The object's content type (such as ``text/html``). If left unset,
        no MIME type is passed to boto3 (which defaults to
        ``binary/octet-stream``).
    """
    print(f"Upload file bucket path: {bucket_path}")
    obj = bucket.Object(bucket_path)

    # Object.put seems to be sensitive to None-type kwargs, so we filter first
    args: Dict[str, Any] = {}
    if metadata is not None and len(metadata) > 0:  # avoid empty Metadata
        args["Metadata"] = metadata
    if acl is not None:
        args["ACL"] = acl
    if cache_control is not None:
        args["CacheControl"] = cache_control
    if content_type is not None:
        args["ContentType"] = content_type

    print("Put args")
    print(args)
    obj.put(Body=content, **args)


def upload_dir_redirect_object(
    *,
    bucket_dir_path: str,
    bucket: Any,
    metadata: Optional[Dict[str, str]] = None,
    acl: Optional[str] = None,
    cache_control: Optional[str] = None,
) -> None:
    """Create an S3 object representing a directory that's designed to
    redirect a browser (via Fastly) to the ``index.html`` contained inside
    that directory.

    Parameters
    ----------
    bucket_dir_path : `str`
        Full name of the object in the S3, which is equivalent to a POSIX
        directory path, like ``dir1/dir2``.
    bucket : boto3 Bucket instance
        S3 bucket.
    metadata : `dict`, optional
        Header metadata values. These keys will appear in headers as
        ``x-amz-meta-*``.
    acl : `str`, optional
        A pre-canned access control list. See
        https://docs.aws.amazon.com/AmazonS3/latest/dev/acl-overview.html#canned-acl
        Default is None, meaning that no ACL is applied to the object.
    cache_control : `str`, optional
        The cache-control header value. For example, ``'max-age=31536000'``.
    """
    # Just the name of the 'directory' itself
    bucket_dir_path = bucket_dir_path.rstrip("/")

    # create a copy of metadata
    if metadata is not None:
        metadata = dict(metadata)
    else:
        metadata = {}

    # header used by LTD's Fastly Varnish config to create a 301 redirect
    metadata["dir-redirect"] = "true"

    upload_object(
        bucket_path=bucket_dir_path,
        bucket=bucket,
        content="",
        metadata=metadata,
        acl=acl,
        cache_control=cache_control,
    )


def presign_post_url_for_prefix(
    *,
    s3: boto3.resources.base.ServiceResource,
    bucket_name: str,
    prefix: str,
    fields: Optional[Dict[str, str]] = None,
    conditions: Optional[Sequence[Collection[str]]] = None,
    expiration: int = 3600,
) -> Dict[str, Any]:
    """Generate a presigned POST URL for clients to upload objects to S3
    without additional authentication.

    Parameters
    ----------
    s3
        S3 service.
    bucket_name : `str`
        Name of the S3 bucket.
    prefix : `str`
        The key prefix in the S3 bucket where objects will be uploaded when
        the presigned POST URL is used. For example, if the prefix is
        ``'myprefix/'`` and the client uploads a file named ``'myfile.txt'``,
        the object will be uploaded with a key of ``myprefix/myfile.txt``.

        .. note::

           Presigned URLs are only useful for uploading files with path
           directories that correspond to the ``prefix``. The upload client
           automatically strips subdirectories from file names when files are
           posted to the presigned URL.
    fields : `dict`
        Dictionary of prefilled form fields. Elements that may be included are
        ``acl``, ``Cache-Control``, ``Content-Type``, ``Content-Disposition``,
        ``Content-Encoding``, ``Expires``, ``success_action_redirect``,
        ``redirect``, ``success_action_status``, and ``x-amz-meta-*``.

        Note that if a particular element is included in the fields dictionary
        it will not be automatically added to the conditions list. You must
        specify a condition for the element as well.
    conditions : `list`
        A list of conditions to include in the policy. For example:
        ``[{"acl": "public-read"}]``.
    expiration : `int`
        The URL's expiration period, in seconds.

    Returns
    -------
    response : `dict`
        A dictionary with keys:

        ``'url'``
            The presigned POST URL.
        ``'fields'``
            A `dict` of key-value pairs that can be passed by clients in the
            data payload of the post.

    Notes
    -----
    For more information, see the boto3 documentation:

    - `S3 Presigned URLs <https://boto3.amazonaws.com/v1/documentation/api/
      latest/guide/s3-presigned-urls.html#generating-a-presigned-url-to-
      upload-a-file>`_.
    - `S3.Client.generate_presigned_post`
    """
    if prefix.endswith("/"):
        key = f"{prefix}${{filename}}"
    else:
        key = f"{prefix}/${{filename}}"

    s3_client = s3.meta.client
    try:
        response = s3_client.generate_presigned_post(
            bucket_name,
            key,
            Fields=fields,
            Conditions=conditions,
            ExpiresIn=expiration,
        )
    except botocore.exceptions.ClientError:
        raise S3Error("Error creating presigned POST URL.")

    # The response contains the presigned URL and required fields
    return response


def presign_post_url_for_directory_object(
    *,
    s3: boto3.resources.base.ServiceResource,
    bucket_name: str,
    key: str,
    fields: Optional[Dict[str, str]] = None,
    conditions: Optional[List[Any]] = None,
    expiration: int = 3600,
) -> Dict[str, Any]:
    """Generate a presigned POST URL for clients to upload directory rediect
    objects to S3 without additional authentication.

    Directory redirect objects are keyed by directory name, do not have a
    trailing slash, and have a ``x-amz-meta-dir-redirect`` header that
    Fastly is configured to redirect a visitor to the corresponding
    ``index.html`` object.

    Parameters
    ----------
    s3
        The S3 service.
    bucket_name : `str`
        Name of the S3 bucket.
    key : `str`
        The key of the directory object in the S3 bucket. This key must not
        have a trailing slash.
    fields : `dict`
        Dictionary of prefilled form fields. Elements that may be included are
        ``acl``, ``Cache-Control``, ``Content-Type``, ``Content-Disposition``,
        ``Content-Encoding``, ``Expires``, ``success_action_redirect``,
        ``redirect``, ``success_action_status``, and ``x-amz-meta-*``.

        Note that if a particular element is included in the fields dictionary
        it will not be automatically added to the conditions list. You must
        specify a condition for the element as well.

        The ``x-amz-meta-dir-redirect`` field is automatically set.
    conditions : `list`
        A list of conditions to include in the policy. For example:
        ``[{"acl": "public-read"}]``.
    expiration : `int`
        The URL's expiration period, in seconds.

    Returns
    -------
    response : `dict`
        A dictionary with keys:

        ``'url'``
            The presigned POST URL.
        ``'fields'``
            A `dict` of key-value pairs that can be passed by clients in the
            data payload of the post.
    """
    key = key.rstrip("/")

    if fields is None:
        fields = {}
    else:
        fields = deepcopy(fields)

    if conditions is None:
        _conditions: List[Any] = []
    else:
        _conditions = deepcopy(conditions)

    # Apply presets for directory redirect objects
    fields["x-amz-meta-dir-redirect"] = "true"
    conditions = set_condition(
        conditions=_conditions,
        condition_key="x-amz-meta-dir-redirect",
        condition={"x-amz-meta-dir-redirect": "true"},
    )

    s3_client = s3.meta.client
    try:
        response = s3_client.generate_presigned_post(
            bucket_name,
            key,
            Fields=fields,
            Conditions=conditions,
            ExpiresIn=expiration,
        )
    except botocore.exceptions.ClientError:
        raise S3Error("Error creating presigned POST URL.")

    # The response contains the presigned URL and required fields
    return response


def format_bucket_prefix(base_prefix: str, dirname: str) -> str:
    """Format an S3 bucket key prefix by joining a base prefix with a directory
    name.
    """
    base_prefix = base_prefix.rstrip("/").lstrip("/")
    dirname = dirname.lstrip("/")
    prefix = "/".join((base_prefix, dirname))
    if not prefix.endswith("/"):
        prefix = prefix + "/"
    return prefix


def set_condition(
    *,
    conditions: List[Collection[str]],
    condition_key: str,
    condition: Collection[str],
) -> List[Collection[str]]:
    """Set a condition on a presigned URL condition list, overwriting an
    existing condition on the same field if necessary.

    For more information about S3 presigned URL conditions, see
    https://docs.aws.amazon.com/AmazonS3/latest/API/sigv4-HTTPPOSTConstructPolicy.html#sigv4-PolicyConditions
    """
    condition_var = "$" + condition_key
    new_conditions = [
        c
        for c in conditions
        if condition_key not in c
        if condition_var not in c
    ]
    new_conditions.append(condition)
    return new_conditions
