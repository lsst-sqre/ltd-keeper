#!/usr/bin/env python
"""
Test S3 directory deletion functionality.

Uses the lsst-the-docs-test bucket in lsst-sqre's account. Also assumes that
credentials for that account are in the ltd-dev profile of ~/.aws/credentials.
"""

import sys
import os.path
app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
sys.path.append(app_path)

from tempfile import TemporaryDirectory
import logging

import boto3

from app.s3 import delete_directory


def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('app.s3').level = logging.DEBUG

    session = boto3.session.Session(profile_name='ltd-dev')
    s3 = session.resource('s3')
    bucket = s3.Bucket('lsst-the-docs-test')

    paths = [
        'test-dir/file1.txt',
        'test-dir/file2.txt',
        'test-dir/dir1/file11.txt',
        'test-dir/dir1/file12.txt',
        'test-dir/dir1/dir11/file111.txt',
        'test-dir/dir1/dir11/file112.txt',
        'test-dir/dir2/file21.txt',
        'test-dir/dir2/file22.txt']

    with TemporaryDirectory() as temp_dir:
        create_test_files(temp_dir, paths)

        for p in paths:
            obj = bucket.Object(p)
            obj.upload_file(os.path.join(temp_dir, p))

        for p in paths:
            obj = list(bucket.objects.filter(Prefix=p))
            assert len(obj) == 1

        delete_directory('lsst-the-docs-test',
                         'test-dir',
                         aws_profile='ltd-dev')

        for p in paths:
            obj = list(bucket.objects.filter(Prefix=p))
            assert len(obj) == 0


def create_test_files(temp_dir, file_list):
    for path in file_list:
        write_file(temp_dir, path)


def write_file(root_dir, rel_path):
    filepath = os.path.join(root_dir, rel_path)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, 'w') as f:
        f.write('Content of {0}'.format(os.path.basename(filepath)))


if __name__ == '__main__':
    main()
