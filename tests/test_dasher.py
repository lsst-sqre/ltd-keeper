"""Tests for dasher module (LTD Dasher dashboard builds)."""

import json
import logging
import responses
import pytest

from app.dasher import build_dashboards
from app.exceptions import DasherError


@responses.activate
def test_build_dashboards():
    """Verify a successful mocked call to ltd-dasher /build."""
    product_urls = ['https://example.org/products/test-product']

    dasher_url = 'http://test-dasher.local:80'
    endpoint_url = dasher_url + '/build'

    # Mock dasher api call
    responses.add(responses.POST, endpoint_url, status=202)

    # Run client function
    build_dashboards(product_urls, dasher_url, logging.getLogger(__name__))

    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == endpoint_url

    # I'm seeing Travis env think that request is a str, while my local
    # machine things it's bytes. Rather odd :/
    if isinstance(responses.calls[0].request.body, bytes):
        request_json = json.loads(responses.calls[0].request.body.decode())
    else:
        request_json = json.loads(responses.calls[0].request.body)
    assert request_json['product_urls'] == product_urls


@responses.activate
def test_skipped_build_dashboards():
    """Check behaviour when LTD_DASHER_URL is not configured."""
    product_urls = ['https://example.org/products/test-product']

    dasher_url = None

    # Run client function
    build_dashboards(product_urls, dasher_url, logging.getLogger(__name__))

    assert len(responses.calls) == 0


@responses.activate
def test_failed_build_dashboards():
    """Verify a failed mocked call to ltd-dasher /build."""
    product_urls = ['https://example.org/products/test-product']

    dasher_url = 'http://test-dasher.local:80'
    endpoint_url = dasher_url + '/build'

    # Mock dasher api call
    responses.add(responses.POST, endpoint_url, status=404)

    # Run client function
    with pytest.raises(DasherError):
        build_dashboards(product_urls, dasher_url, logging.getLogger(__name__))

    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == endpoint_url
