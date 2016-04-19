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

from app.s3 import delete_directory


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
    with tempfile.TemporaryDirectory() as temp_dir:
        for p in file_paths:
            full_path = os.path.join(temp_dir, p)
            full_dir = os.path.dirname(full_path)
            os.makedirs(full_dir)
            with open(full_path, 'w') as f:
                f.write('content')
            obj = bucket.Object(bucket_root + p)
            obj.upload_file(full_path)

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
