#!/usr/bin/env python
"""Integrations test for ltd-keeper's Route 53 interactions.

ltdtest.local. is a test Route 53 hosted zone created in the lsst-sqre AWS
account.
"""
import sys
import os.path
app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))  # NOQA
sys.path.append(app_path)  # NOQA

import boto3
import logging

from app.route53 import create_cname, delete_cname
from app.route53 import _find_cname_record, _get_zone_id


def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('app.route53').level = logging.DEBUG

    # profile in ~/.aws/credentials with lsst-sqre account credentials
    aws_profile_name = 'ltd-dev'
    session = boto3.session.Session(profile_name=aws_profile_name)
    route53 = session.client('route53')

    zone_id = _get_zone_id(route53, 'ltdtest.local.')
    print('Creating CNAME')
    create_cname('docs.ltdtest.local.', 'daringfireball.net',
                 aws_profile=aws_profile_name)
    record = _find_cname_record(route53, zone_id, 'docs.ltdtest.local.')
    assert record is not None
    print(record)

    print('Changing CNAME')
    create_cname('docs.ltdtest.local.', 'www.lsst.org',
                 aws_profile=aws_profile_name)
    record = _find_cname_record(route53, zone_id, 'docs.ltdtest.local.')
    assert record is not None
    print(record)

    print('Deleting CNAME')
    delete_cname('docs.ltdtest.local.', aws_profile=aws_profile_name)
    record = _find_cname_record(route53, zone_id, 'docs.ltdtest.local.')
    assert record is None
    print(record)


if __name__ == '__main__':
    main()
