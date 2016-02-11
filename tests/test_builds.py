"""Tests for the builds API."""

import pytest

from app.exceptions import ValidationError


def test_builds(client):
    # Add a sample product
    p = {'slug': 'lsst_apps',
         'doc_repo': 'https://github.com/lsst/pipelines_docs.git',
         'title': 'LSST Science Pipelines',
         'domain': 'pipelines.lsst.io',
         'bucket_name': 'bucket-name'}
    r = client.post('/v1/products/', p)
    assert r.status == 201

    prod_url = client.get('/v1/products/lsst_apps').json['self_url']

    # Initially no builds
    r = client.get('/v1/products/lsst_apps/builds/')
    assert r.status == 200
    assert len(r.json['builds']) == 0

    # Add a build
    b1 = {'slug': 'b1'}
    r = client.post('/v1/products/lsst_apps/builds/', b1)
    assert r.status == 201
    assert r.json['product_url'] == prod_url
    assert r.json['slug'] == b1['slug']
    assert r.json['date_created'] is not None
    assert r.json['date_ended'] is None
    assert r.json['uploaded'] is False

    # Re-add build with same slug; should fail
    with pytest.raises(ValidationError):
        r = client.post('/v1/products/lsst_apps/builds/', b1)

    # List builds
    r = client.get('/v1/products/lsst_apps/builds/')
    assert r.status == 200
    assert len(r.json['builds']) == 1

    # Get build
    r = client.get('/v1/builds/1')
    assert r.status == 200
    assert r.json['bucket_name'] == 'bucket-name'
    assert r.json['bucket_root_dir'] == 'lsst_apps/builds/b1'

    # Register upload
    r = client.post('/v1/builds/1/uploaded', {})
    assert r.status == 202

    r = client.get('/v1/builds/1')
    assert r.json['uploaded'] is True

    # Deprecate build
    r = client.delete('/v1/builds/1')
    assert r.status == 202

    r = client.get('/v1/builds/1')
    assert r.json['product_url'] == prod_url
    assert r.json['slug'] == b1['slug']
    assert r.json['date_created'] is not None
    assert r.json['date_ended'] is not None

    # Add some auto-slugged builds
    r = client.post('/v1/products/lsst_apps/builds/', {'foo': 'bar'})
    assert r.status == 201
    assert r.json['slug'] == '1'

    r = client.post('/v1/products/lsst_apps/builds/', {'foo': 'bar'})
    assert r.status == 201
    assert r.json['slug'] == '2'
