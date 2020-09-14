"""Functions for working with Amazon AWS Route 53 for managing domains.

:func:`create_cname` and :func:`delete_cname` create and delete CNAMES with
AWS Route 53.
"""

from __future__ import annotations

from pprint import pformat
from typing import TYPE_CHECKING, Any, Dict, Optional

import boto3
from structlog import get_logger

from keeper.exceptions import Route53Error

if TYPE_CHECKING:
    import botocore.client.Route53

__all__ = ["create_cname", "delete_cname"]


def create_cname(
    cname_domain: str,
    origin_domain: str,
    aws_access_key_id: str,
    aws_secret_access_key: str,
) -> None:
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
    aws_access_key_id : str
        The access key for your AWS account. Also set `aws_secret_access_key`.
    aws_secret_access_key : str
        The secret key for your AWS account.

    Raises
    ------
    app.exceptions.Route53Error
        Any error with Route 53 usage.
    """
    logger = get_logger(__name__)
    logger.info(
        "create_cname", cname_domain=cname_domain, origin_domain=origin_domain
    )

    if not cname_domain.endswith("."):
        cname_domain = cname_domain + "."
    if origin_domain.endswith("."):
        origin_domain = origin_domain.lstrip(".")

    session = boto3.session.Session(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )
    client = session.client("route53")
    zone_id = _get_zone_id(client, cname_domain)
    _upsert_cname_record(client, zone_id, cname_domain, origin_domain)


def delete_cname(
    cname_domain: str, aws_access_key_id: str, aws_secret_access_key: str
) -> None:
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
    aws_access_key_id : str
        The access key for your AWS account. Also set `aws_secret_access_key`.
    aws_secret_access_key : str
        The secret key for your AWS account.

    Raises
    ------
    app.exceptions.Route53Error
        Any error with Route 53 usage.
    """
    logger = get_logger(__name__)
    logger.info("delete_cname", cname_domain=cname_domain)

    if not cname_domain.endswith("."):
        cname_domain = cname_domain + "."

    session = boto3.session.Session(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )
    client = session.client("route53")

    zone_id = _get_zone_id(client, cname_domain)
    record = _find_cname_record(client, zone_id, cname_domain)
    if record is None:
        logger.info(f"Did not delete {cname_domain} because it does not exist")
        return

    # Build the change set for change_resource_record_sets. This method
    # needs to know the TTL for the specific record to update; although
    # we only use single records.
    # http://docs.aws.amazon.com/Route53/latest/APIReference/API_ChangeResourceRecordSets.html
    change: Any = {
        "Action": "DELETE",
        "ResourceRecordSet": {
            "Name": cname_domain,
            "Type": "CNAME",
            "ResourceRecords": record["ResourceRecords"],
        },
    }
    if "TTL" in record:
        change["ResourceRecordSet"]["TTL"] = record["TTL"]
    if "SetIdentifier" in record:
        change["ResourceRecordSet"]["SetIdentifier"] = record["SetIdentifier"]

    change_batch = {
        "Comment": "DELETE {0}".format(cname_domain),
        "Changes": [change],
    }
    logger.info(
        "Created change batch for cname delete", change_batch=change_batch
    )

    r = client.change_resource_record_sets(
        HostedZoneId=zone_id, ChangeBatch=change_batch
    )
    logger.info("cname delete response", response=r, change_batch=change_batch)
    if r["ResponseMetadata"]["HTTPStatusCode"] == 400:
        msg = "delete_cname failed with:\n" + pformat(change)
        raise Route53Error(msg)


def _get_zone_id(client: botocore.client.Route53, domain: str) -> str:
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
    logger = get_logger(__name__)
    assert domain.endswith(".")

    # Filter out sub-domains; leaves domains intact
    fsd = ".".join(domain.split(".")[-3:])

    # Find zone from Route 53 api
    zones = client.list_hosted_zones()
    zone_id = None
    for z in zones["HostedZones"]:
        if fsd == z["Name"]:
            zone_id = z["Id"]

    if zone_id is None:
        msg = "Could not find hosted zone for fully specified domain"
        logger.error(msg, domain=fsd, zones=zones)
        logger.error(pformat(zones))
        raise Route53Error(msg)

    logger.info("Got HostedZoneId", zone_id=zone_id)
    return zone_id


def _find_cname_record(
    client: botocore.client.Route53, zone_id: str, cname_domain: str
) -> Optional[Dict[str, Any]]:
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

        `None` is returned is no ResourceRecordSet matching ``cname_domain`` is
        found.
    """
    logger = get_logger(__name__)

    # turns out boto3 doesn't need StardRecordName in lexicographic order
    # despite their docs.
    # name = _lexicographic_order_domain(cname_url)

    if not cname_domain.endswith("."):
        cname_domain = cname_domain + "."

    r = client.list_resource_record_sets(
        HostedZoneId=zone_id,
        StartRecordName=cname_domain,
        StartRecordType="CNAME",
    )
    if r["ResponseMetadata"]["HTTPStatusCode"] != 200:
        msg = "list_resource_record_sets failed"
        logger.error(msg, response=r)
        raise Route53Error(msg)
    for record in r["ResourceRecordSets"]:
        if record["Name"] == cname_domain:
            logger.info("Got Resource Record Set", record=record)
            return record

    logger.info("No existing CNAME record found", cname_domain=cname_domain)
    return None


def _upsert_cname_record(
    client: botocore.client.Route53,
    zone_id: str,
    cname_domain: str,
    origin_domain: str,
) -> None:
    """Upsert a CNAME record of `cname_domain` pointint to `origin_domain`."""
    logger = get_logger(__name__)

    change = {
        "Action": "UPSERT",
        "ResourceRecordSet": {
            "Name": cname_domain,
            "Type": "CNAME",
            "TTL": 900,
            "ResourceRecords": [{"Value": origin_domain}],
        },
    }
    change_batch = {
        "Comment": "Upsert {0} -> {1}".format(cname_domain, origin_domain),
        "Changes": [change],
    }
    logger.info("Created cname record change batch", change_batch=change_batch)

    r = client.change_resource_record_sets(
        HostedZoneId=zone_id, ChangeBatch=change_batch
    )
    logger.info("Change resource record set", response=r)
    if r["ResponseMetadata"]["HTTPStatusCode"] != 200:
        msg = ("change_resource_record_sets failed",)
        logger.error(msg, change=change, response=r)
        raise Route53Error(msg)
