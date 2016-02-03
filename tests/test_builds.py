"""Tests for the builds API."""


def test_builds(client):
    # Add a sample product
    p = {'eups_package': 'lsst_apps',
         'doc_repo': 'https://github.com/lsst/pipelines_docs.git',
         'name': 'LSST Science Pipelines',
         'domain': 'pipelines.lsst.io',
         'build_bucket': 'bucket-name'}
    r = client.post('/v1/products/', p)
    assert r.status == 201

    prod_url = client.get('/v1/products/1').json['self_url']

    # Intially no builds
    r = client.get('/v1/products/1/builds/')
    assert r.status == 200
    assert len(r.json['builds']) == 0

    # Add a build
    b1 = {'name': 'b1'}
    r = client.post('/v1/products/1/builds/', b1)
    assert r.status == 201

    # List builds
    r = client.get('/v1/products/1/builds/')
    assert r.status == 200
    assert len(r.json['builds']) == 1

    # Get build
    r = client.get('/v1/builds/1')
    assert r.json['product_url'] == prod_url
    assert r.json['name'] == b1['name']
    assert r.json['creation_date'] is not None
    assert r.json['end_date'] is None

    # Deprecate build
    r = client.post('/v1/builds/1/deprecate', {})
    assert r.status == 202

    r = client.get('/v1/builds/1')
    assert r.json['product_url'] == prod_url
    assert r.json['name'] == b1['name']
    assert r.json['creation_date'] is not None
    assert r.json['end_date'] is not None
