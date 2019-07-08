"""Tests for s3 module (S3 utilities)

These tests required the following environment variables:

``LTD_KEEPER_TEST_AWS_ID``
    AWS access key ID

``LTD_KEEPER_TEST_AWS_SECRET``
    AWS secret access key

``LTD_KEEPER_TEST_BUCKET``
    Name of an S3 bucket that already exists and can be used for testing.

The tests will be skipped if they are not available.

Note that this test will create a random uuid4) directory at the root of
``LTD_KEEPER_TEST_BUCKET``, though the test harness will attempt to delete
it.
"""

import tempfile
import os
import uuid

import boto3
import pytest

from keeper.s3 import delete_directory, copy_directory, format_bucket_prefix


@pytest.mark.skipif(os.getenv('LTD_KEEPER_TEST_AWS_ID') is None or
                    os.getenv('LTD_KEEPER_TEST_AWS_SECRET') is None or
                    os.getenv('LTD_KEEPER_TEST_BUCKET') is None,
                    reason='Set LTD_KEEPER_TEST_AWS_ID, '
                           'LTD_KEEPER_TEST_AWS_SECRET and '
                           'LTD_KEEPER_TEST_BUCKET')
def test_delete_directory(request):
    session = boto3.session.Session(
        aws_access_key_id=os.getenv('LTD_KEEPER_TEST_AWS_ID'),
        aws_secret_access_key=os.getenv('LTD_KEEPER_TEST_AWS_SECRET'))
    s3 = session.resource('s3')
    bucket = s3.Bucket(os.getenv('LTD_KEEPER_TEST_BUCKET'))

    bucket_root = str(uuid.uuid4()) + '/'

    def cleanup():
        print("Cleaning up the bucket")
        delete_directory(os.getenv('LTD_KEEPER_TEST_BUCKET'),
                         bucket_root,
                         os.getenv('LTD_KEEPER_TEST_AWS_ID'),
                         os.getenv('LTD_KEEPER_TEST_AWS_SECRET'))
    request.addfinalizer(cleanup)

    file_paths = ['a/test1.txt', 'a/b/test2.txt', 'a/b/c/test3.txt']
    _upload_files(file_paths, bucket, bucket_root,
                  'sample-key', 'max-age=3600', 'text/plain')

    # Delete b/*
    delete_directory(os.getenv('LTD_KEEPER_TEST_BUCKET'),
                     bucket_root + 'a/b/',
                     os.getenv('LTD_KEEPER_TEST_AWS_ID'),
                     os.getenv('LTD_KEEPER_TEST_AWS_SECRET'))

    # Ensure paths outside of that are still available, but paths in b/ are
    # deleted
    bucket_paths = []
    for obj in bucket.objects.filter(Prefix=bucket_root):
        if obj.key.endswith('/'):
            continue
        bucket_paths.append(obj.key)

    for p in file_paths:
        bucket_path = bucket_root + p
        if p.startswith('a/b'):
            assert bucket_path not in bucket_paths
        else:
            assert bucket_path in bucket_paths

    # Attempt to delete an empty prefix. Ensure it does not raise an exception.
    delete_directory(os.getenv('LTD_KEEPER_TEST_BUCKET'),
                     bucket_root + 'empty-prefix/',
                     os.getenv('LTD_KEEPER_TEST_AWS_ID'),
                     os.getenv('LTD_KEEPER_TEST_AWS_SECRET'))


@pytest.mark.skipif(os.getenv('LTD_KEEPER_TEST_AWS_ID') is None or
                    os.getenv('LTD_KEEPER_TEST_AWS_SECRET') is None or
                    os.getenv('LTD_KEEPER_TEST_BUCKET') is None,
                    reason='Set LTD_KEEPER_TEST_AWS_ID, '
                           'LTD_KEEPER_TEST_AWS_SECRET and '
                           'LTD_KEEPER_TEST_BUCKET')
def test_copy_directory(request):
    session = boto3.session.Session(
        aws_access_key_id=os.getenv('LTD_KEEPER_TEST_AWS_ID'),
        aws_secret_access_key=os.getenv('LTD_KEEPER_TEST_AWS_SECRET'))
    s3 = session.resource('s3')
    bucket = s3.Bucket(os.getenv('LTD_KEEPER_TEST_BUCKET'))

    bucket_root = str(uuid.uuid4()) + '/'

    def cleanup():
        print("Cleaning up the bucket")
        delete_directory(os.getenv('LTD_KEEPER_TEST_BUCKET'),
                         bucket_root,
                         os.getenv('LTD_KEEPER_TEST_AWS_ID'),
                         os.getenv('LTD_KEEPER_TEST_AWS_SECRET'))
    request.addfinalizer(cleanup)

    initial_paths = ['test1.txt', 'test2.txt', 'aa/test3.txt']
    new_paths = ['test4.txt', 'bb/test5.txt']

    # add old and new file sets
    _upload_files(initial_paths, bucket, bucket_root + 'a/',
                  'sample-key', 'max-age=3600', 'text/plain')
    _upload_files(new_paths, bucket, bucket_root + 'b/',
                  'sample-key', 'max-age=3600', 'text/plain')

    # copy files
    copy_directory(
        bucket_name=os.getenv('LTD_KEEPER_TEST_BUCKET'),
        src_path=bucket_root + 'b/',
        dest_path=bucket_root + 'a/',
        aws_access_key_id=os.getenv('LTD_KEEPER_TEST_AWS_ID'),
        aws_secret_access_key=os.getenv('LTD_KEEPER_TEST_AWS_SECRET'),
        surrogate_key='new-key',
        surrogate_control='max-age=31536000',
        cache_control='no-cache')

    # Test files in the a/ directory are from b/
    for obj in bucket.objects.filter(Prefix=bucket_root + 'a/'):
        bucket_path = os.path.relpath(obj.key, start=bucket_root + 'a/')
        assert bucket_path in new_paths
        # ensure correct metadata
        head = s3.meta.client.head_object(
            Bucket=os.getenv('LTD_KEEPER_TEST_BUCKET'),
            Key=obj.key)
        assert head['CacheControl'] == 'no-cache'
        assert head['ContentType'] == 'text/plain'
        assert head['Metadata']['surrogate-key'] == 'new-key'
        assert head['Metadata']['surrogate-control'] == 'max-age=31536000'

    # Test that a directory object exists
    bucket_paths = [obj.key
                    for obj in bucket.objects.filter(Prefix=bucket_root + 'a')]
    assert os.path.join(bucket_root, 'a') in bucket_paths


def test_copy_dir_src_in_dest():
    """Test that copy_directory fails raises an assertion error if source in
    destination.
    """
    with pytest.raises(AssertionError):
        copy_directory('example', 'dest/src', 'dest', 'id', 'key')


def test_copy_dir_dest_in_src():
    """Test that copy_directory fails raises an assertion error if destination
    is part of the source.
    """
    with pytest.raises(AssertionError):
        copy_directory('example', 'src', 'src/dest', 'id', 'key')


def _upload_files(file_paths, bucket, bucket_root,
                  surrogate_key, cache_control, content_type):
    with tempfile.TemporaryDirectory() as temp_dir:
        for p in file_paths:
            full_path = os.path.join(temp_dir, p)
            full_dir = os.path.dirname(full_path)
            os.makedirs(full_dir, exist_ok=True)
            with open(full_path, 'w') as f:
                f.write('content')

            extra_args = {
                'Metadata': {'surrogate-key': surrogate_key},
                'ContentType': content_type,
                'CacheControl': cache_control}
            obj = bucket.Object(bucket_root + p)
            obj.upload_file(full_path, ExtraArgs=extra_args)


@pytest.mark.parametrize(
    'base_prefix, dirname, expected',
    [
        ('base/prefix', 'a', 'base/prefix/a/'),
        ('/base/prefix/', 'a/', 'base/prefix/a/'),
        ('base/prefix', 'a/b', 'base/prefix/a/b/'),
        ('base/prefix', '/', 'base/prefix/'),
        ('base/prefix', '', 'base/prefix/')
    ]
)
def test_format_bucket_prefix(base_prefix, dirname, expected):
    assert expected == format_bucket_prefix(base_prefix, dirname)
