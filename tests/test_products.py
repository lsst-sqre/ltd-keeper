"""Tests for the product API."""


def test_products(client):
    r = client.get('/v1/products/')
    assert r.status == 200
    assert len(r.json['products']) == 0

    # Add first product
    p1 = {'eups_package': 'lsst_apps',
          'doc_repo': 'https://github.com/lsst/pipelines_docs.git',
          'name': 'LSST Science Pipelines',
          'domain': 'pipelines.lsst.io',
          'build_bucket': 'bucket-name'}
    r = client.post('/v1/products/', p1)
    assert r.status == 201
    p1_url = r.headers['Location']

    # Add second product
    p2 = {'eups_package': 'qserv',
          'doc_repo': 'https://github.com/lsst/qserv_docs.git',
          'name': 'Qserv',
          'domain': 'qserv.lsst.io',
          'build_bucket': 'bucket-name'}
    r = client.post('/v1/products/', p2)
    assert r.status == 201
    p2_url = r.headers['Location']

    # Test listing of products
    r = client.get('/v1/products/')
    assert r.status == 200
    assert r.json['products'] == [p1_url, p2_url]

    # Test getting a product
    r = client.get(p1_url)
    for k, v in p1.items():
        assert r.json[k] == v

    r = client.get(p2_url)
    for k, v in p2.items():
        assert r.json[k] == v

    p2v2 = dict(p2)
    p2v2['build_bucket'] = 'different-bucket'

    # # Try modifying non-existant product
    # # Throws werkzeug.exceptions.NotFound rather than emitting 404 response
    # r = client.put('/v1/products/3', p2v2)
    # assert r.status == 404

    # Modify existing product
    r = client.put('/v1/products/2', p2v2)
    assert r.status == 200
    r = client.get('/v1/products/2')
    for k, v in p2v2.items():
        assert r.json[k] == v
