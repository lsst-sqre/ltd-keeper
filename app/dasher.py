"""Interaction with LTD Dasher microservices (for building static dashboards
of product editions and builds.
"""

import requests

from .exceptions import DasherError


def build_dashboards(product_urls, dasher_url):
    """Trigger ltd-dasher's POST /build endpoint to build dashboards for one
    or more LTD products.

    This function is a no-op if the LTD_DASHER_URL app config is ``None``.

    Parameters
    ----------
    product_urls : `list` or `tuple` of `str`
        Sequence of LTD Keeper product URLs for products whose dashboards
        should be rebuilt.
    dasher_url : `str`
        Root URL of the dasher service in the Kubernetes cluster. Should be
        the value of the ``LTD_DASHER_URL`` configuration.

    Raises
    ------
    DasherError
    """
    assert isinstance(product_urls, (list, tuple))

    if dasher_url is None:
        # skip if not configured
        return

    dasher_build_url = '{0}/build'.format(dasher_url)
    request_data = {'product_urls': product_urls}
    r = requests.post(dasher_build_url, json=request_data)

    if r.status_code != 202:
        raise DasherError('Dasher error (status {0})'.format(r.status_code))
