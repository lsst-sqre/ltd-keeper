"""Functions for working with Amazon AWS Route 53 for managing domains.

:func:`create_cname` and :func:`delete_cname` create and delete CNAMES with
AWS Route 53.
"""

from pprint import pformat
import logging

import boto3

from .exceptions import Route53Error

__all__ = ['create_cname', 'delete_cname']


log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def create_cname(cname_domain, origin_domain, aws_profile='default'):
    """Create a CNAME `cname_domain` that points to resources at
    `origin_domain`.

    This function technically performs an *upsert* so that an existing
    CNAME record for `cname_domain` will be updated to point to the new
    `origin_domain`.

    **Note:** This function creates a simple `cname_domain` and doesn't yet
    work with multiple geographically distributed CNAME records.

    Parameters
    ----------
    cname_domain : str
        The CNAME domain. It should be a fully qualified domain that ends
        in a dot (e.g., ``'my.domain.org.'``). A dot will be appended as a
        convenvience.

        Note that a CNAME domain should be a *sub-domain*. This function
        does not configure the A (apex) record (e.g. ``'domain.org'``).
    origin_domain : str
        The original domain of the resource (e.g., ``'a-domain.org'``).
        This should not be a fully qualified domain, but any trailing dot
        will be stripped as a convenience.
    aws_profile : str
        Name of an AWS credential profile in :file:`~/.aws/credentials`
        that has access to the needed Route 53 hosted zone.

    Raises
    ------
    app.exceptions.Route53Error
        Any error with Route 53 usage.
    """
    log.info('create_cname({0}, {1})'.format(cname_domain, origin_domain))

    if not cname_domain.endswith('.'):
        cname_domain = cname_domain + '.'
    if origin_domain.endswith('.'):
        origin_domain = origin_domain.lstrip('.')

    session = boto3.session.Session(profile_name=aws_profile)
    client = session.client('route53')
    zone_id = _get_zone_id(client, cname_domain)
    _upsert_cname_record(client, zone_id, cname_domain, origin_domain)


def delete_cname(cname_domain, aws_profile='default'):
    """Delete a CNAME for `cname_domain`

    **Note:** This function deletes the first matching CNAME records and
    doesn't yet work with multiple geographically distributed CNAME records.

    Parameters
    ----------
    cname_domain : str
        The CNAME domain. It should be a fully qualified domain that ends
        in a dot (e.g., ``'my.domain.org.'``). A dot will be appended as a
        convenvience.

        Note that a CNAME domain should be a *sub-domain*. This function
        does not configure the A (apex) record (e.g. ``'domain.org'``).
    aws_profile : str, optional
        Name of an AWS credential profile in :file:`~/.aws/credentials`
        that has access to the needed Route 53 hosted zone.

    Raises
    ------
    app.exceptions.Route53Error
        Any error with Route 53 usage.
    """
    log.info('delete_cname({0})'.format(cname_domain))

    if not cname_domain.endswith('.'):
        cname_domain = cname_domain + '.'

    session = boto3.session.Session(profile_name=aws_profile)
    client = session.client('route53')

    zone_id = _get_zone_id(client, cname_domain)
    record = _find_cname_record(client, zone_id, cname_domain)

    # Build the change set for change_resource_record_sets. This method
    # needs to know the TTL for the specific record to update; although
    # we only use single records.
    # http://docs.aws.amazon.com/Route53/latest/APIReference/API_ChangeResourceRecordSets.html
    change = {
        'Action': 'DELETE',
        'ResourceRecordSet': {
            'Name': cname_domain,
            'Type': 'CNAME',
            'ResourceRecords': record['ResourceRecords']
        }
    }
    if 'TTL' in record:
        change['ResourceRecordSet']['TTL'] = record['TTL']
    if 'SetIdentifier' in record:
        change['ResourceRecordSet']['SetIdentifier'] = record['SetIdentifier']

    change_batch = {
        'Comment': 'DELETE {0}'.format(cname_domain),
        'Changes': [change],
    }
    log.info(pformat(change_batch))

    r = client.change_resource_record_sets(
        HostedZoneId=zone_id,
        ChangeBatch=change_batch)
    log.info(r)
    if r['ResponseMetadata']['HTTPStatusCode'] == 400:
        msg = 'delete_cname failed with:\n' + pformat(change)
        raise Route53Error(msg)


def _get_zone_id(client, domain):
    """Get the ID of the Hosted Zone that services this `domain`.

    Parameters
    ---------
    client :
        Boto3 Route 53 client.
    url : str
        A fully specified domain (ethat ends in a dot, ``'.'``, e.g.
        ``'domain.org.'``). A sub-domain can also be provded
        (e.g. ``'my.domain.org.'``).

    Returns
    -------
    zone_id : str
        Route 53 Hosted Zone ID that services the domain.
    """
    assert domain.endswith('.')

    # Filter out sub-domains; leaves domains intact
    fsd = '.'.join(domain.split('.')[-3:])

    # Find zone from Route 53 api
    zones = client.list_hosted_zones()
    zone_id = None
    for z in zones['HostedZones']:
        if fsd == z['Name']:
            zone_id = z['Id']

    if zone_id is None:
        msg = 'Could not find hosted zone for fully specified ' \
              'domain: {0}'.format(fsd)
        log.error(msg)
        log.error(pformat(zones))
        raise Route53Error(msg)

    log.info('Using HostedZoneId: {0}'.format(zone_id))
    return zone_id


def _find_cname_record(client, zone_id, cname_domain):
    """Find an existing record for the `cname_domain`, or `None` if one does
    not exist.

    Parameters
    ----------
    client :
        Boto3 Route 53 client.
    zone_id : str
        The Hosted Zone ID for the CNAME.
    cname_domain : str
        The CNAME domain, which is a fully qualified domain ending in a dot.
        http://docs.aws.amazon.com/Route53/latest/DeveloperGuide/ResourceRecordTypes.html#CNAMEFormat

    Returns
    -------
    record : dict
        The ``ResourceRecordSet`` with a ``Name`` corresponding to the
        `cname_domain`. E.g.,

        .. code-block:: python

           [{'Name': 'www.mydomain.org.',
             'ResourceRecords': [{'Value': 'origin_domain.com'}],
             'TTL': 14400,
             'Type': 'CNAME'}]

        `None` is return is not ResourceRecordSet matching `cname_domain` is
        found.
    """
    # turns out boto3 doesn't need StardRecordName in lexicographic order
    # despite their docs.
    # name = _lexicographic_order_domain(cname_url)

    if not cname_domain.endswith('.'):
        cname_domain = cname_domain + '.'

    r = client.list_resource_record_sets(
        HostedZoneId=zone_id,
        StartRecordName=cname_domain,
        StartRecordType='CNAME'
    )
    if r['ResponseMetadata']['HTTPStatusCode'] != 200:
        msg = 'list_resource_record_sets failed:\n' + pformat(r)
        log.error(msg)
        raise Route53Error(msg)
    for record in r['ResourceRecordSets']:
        if record['Name'] == cname_domain:
            log.info(pformat(record))
            return record

    log.info('No existing CNAME record found for {0}'.format(cname_domain))
    return None


def _upsert_cname_record(client, zone_id, cname_domain, origin_domain):
    """Upsert a CNAME record of `cname_domain` that points to `origin_domain`.
    """
    change = {
        'Action': 'UPSERT',
        'ResourceRecordSet': {
            'Name': cname_domain,
            'Type': 'CNAME',
            'TTL': 900,
            'ResourceRecords': [
                {
                    'Value': origin_domain
                },
            ],
        }
    }
    change_batch = {
        'Comment': 'Upsert {0} -> {1}'.format(cname_domain, origin_domain),
        'Changes': [change]}
    log.info(pformat(change_batch))

    r = client.change_resource_record_sets(
        HostedZoneId=zone_id,
        ChangeBatch=change_batch)
    log.info(r)
    if r['ResponseMetadata']['HTTPStatusCode'] != 200:
        msg = 'change_resource_record_sets failed with:\n' + pformat(change)
        log.error(msg)
        raise Route53Error(msg)
