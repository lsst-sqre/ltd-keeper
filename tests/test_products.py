"""Tests for the product API."""


def test_products(client):
    r = client.get('/products/')
    assert r.status == 200
    assert len(r.json['products']) == 0

    # Add first product
    p1 = {'slug': 'lsst_apps',
          'doc_repo': 'https://github.com/lsst/pipelines_docs.git',
          'title': 'LSST Science Pipelines',
          'domain': 'pipelines.lsst.io',
          'bucket_name': 'bucket-name'}
    r = client.post('/products/', p1)
    assert r.status == 201
    p1_url = r.headers['Location']

    # Add second product
    p2 = {'slug': 'qserv',
          'doc_repo': 'https://github.com/lsst/qserv_docs.git',
          'title': 'Qserv',
          'domain': 'qserv.lsst.io',
          'bucket_name': 'bucket-name'}
    r = client.post('/products/', p2)
    assert r.status == 201
    p2_url = r.headers['Location']

    # Test listing of products
    r = client.get('/products/')
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
    p2v2['bucket_name'] = 'bucket_name'

    # # Try modifying non-existant product
    # # Throws werkzeug.exceptions.NotFound rather than emitting 404 response
    # r = client.put('/products/3', p2v2)
    # assert r.status == 404

    # Modify existing product
    r = client.put('/products/qserv', p2v2)
    assert r.status == 200
    r = client.get('/products/qserv')
    for k, v in p2v2.items():
        assert r.json[k] == v
