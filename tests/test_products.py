"""Tests for the product API."""

import pytest
from werkzeug.exceptions import NotFound
from keeper.exceptions import ValidationError


def test_products(client):
    r = client.get('/products/')
    assert r.status == 200
    assert len(r.json['products']) == 0

    # Add first product
    p1 = {'slug': 'pipelines',
          'doc_repo': 'https://github.com/lsst/pipelines_docs.git',
          'title': 'LSST Science Pipelines',
          'root_domain': 'lsst.io',
          'root_fastly_domain': 'global.ssl.fastly.net',
          'bucket_name': 'bucket-name'}
    r = client.post('/products/', p1)
    assert r.status == 201
    p1_url = r.headers['Location']

    # Validate that default edition was made
    r = client.get('/products/pipelines/editions/')
    assert r.status == 200
    default_ed_url = r.json['editions'][0]
    r = client.get(default_ed_url)
    assert r.json['slug'] == 'main'
    assert r.json['title'] == 'Latest'
    assert r.json['tracked_refs'] == ['master']
    assert r.json['published_url'] == 'https://pipelines.lsst.io'

    # Add second product
    p2 = {'slug': 'qserv',
          'doc_repo': 'https://github.com/lsst/qserv_docs.git',
          'title': 'Qserv',
          'root_domain': 'lsst.io',
          'root_fastly_domain': 'global.ssl.fastly.net',
          'bucket_name': 'bucket-name'}
    r = client.post('/products/', p2)
    assert r.status == 201
    p2_url = r.headers['Location']

    # Add product with slug that will fail validation
    with pytest.raises(ValidationError):
        client.post('/products/',
                    {'slug': '0qserv',
                     'doc_repo': 'https://github.com/lsst/qserv_docs.git',
                     'title': 'Qserv',
                     'root_domain': 'lsst.io',
                     'root_fastly_domain': 'global.ssl.fastly.net',
                     'bucket_name': 'bucket-name'})
    with pytest.raises(ValidationError):
        client.post('/products/',
                    {'slug': 'qserv_distrib',
                     'doc_repo': 'https://github.com/lsst/qserv_docs.git',
                     'title': 'Qserv',
                     'root_domain': 'lsst.io',
                     'root_fastly_domain': 'global.ssl.fastly.net',
                     'bucket_name': 'bucket-name'})
    with pytest.raises(ValidationError):
        client.post('/products/',
                    {'slug': 'qserv.distrib',
                     'doc_repo': 'https://github.com/lsst/qserv_docs.git',
                     'title': 'Qserv',
                     'root_domain': 'lsst.io',
                     'root_fastly_domain': 'global.ssl.fastly.net',
                     'bucket_name': 'bucket-name'})

    # Test listing of products
    r = client.get('/products/')
    assert r.status == 200
    assert r.json['products'] == [p1_url, p2_url]

    # Test getting a product
    r = client.get(p1_url)
    for k, v in p1.items():
        assert r.json[k] == v
    # Test domain
    assert r.json['domain'] == 'pipelines.lsst.io'
    assert r.json['fastly_domain'] == 'global.ssl.fastly.net'
    assert r.json['published_url'] == 'https://pipelines.lsst.io'
    # Test surrogate key
    assert len(r.json['surrogate_key']) == 32

    r = client.get(p2_url)
    for k, v in p2.items():
        assert r.json[k] == v
    # Test domain
    assert r.json['domain'] == 'qserv.lsst.io'
    assert r.json['fastly_domain'] == 'global.ssl.fastly.net'
    assert r.json['published_url'] == 'https://qserv.lsst.io'
    # Test surrogate key
    assert len(r.json['surrogate_key']) == 32

    p2v2 = dict(p2)
    p2v2['title'] = 'Qserve Data Access'

    # # Try modifying non-existant product
    # # Throws werkzeug.exceptions.NotFound rather than emitting 404 response
    # r = client.put('/products/3', p2v2)
    # assert r.status == 404

    # Modify existing product
    r = client.patch('/products/qserv', p2v2)
    assert r.status == 200
    r = client.get('/products/qserv')
    assert r.status == 200
    print(r.json)
    for k, v in p2v2.items():
        assert r.json[k] == v


# Authorizion tests: POST /products/ =========================================
# Only the full admin client and the product-authorized client should get in


def test_post_product_auth_anon(anon_client):
    r = anon_client.post('/products/', {'foo': 'bar'})
    assert r.status == 401


def test_post_product_auth_product_client(product_client):
    with pytest.raises(ValidationError):
        product_client.post('/products/', {'foo': 'bar'})


def test_post_product_auth_edition_client(edition_client):
    r = edition_client.post('/products/', {'foo': 'bar'})
    assert r.status == 403


def test_post_product_auth_builduploader_client(upload_build_client):
    r = upload_build_client.post('/products/', {'foo': 'bar'})
    assert r.status == 403


def test_post_product_auth_builddeprecator_client(upload_build_client):
    r = upload_build_client.post('/products/', {'foo': 'bar'})
    assert r.status == 403


# Authorizion tests: PATCH /products/<slug> ==================================
# Only the full admin client and the product-authorized client should get in


def test_patch_product_auth_anon(anon_client):
    r = anon_client.patch('/products/test', {'foo': 'bar'})
    assert r.status == 401


def test_patch_product_auth_product_client(product_client):
    with pytest.raises(NotFound):
        product_client.patch('/products/test', {'foo': 'bar'})


def test_patch_product_auth_edition_client(edition_client):
    r = edition_client.patch('/products/test', {'foo': 'bar'})
    assert r.status == 403


def test_patch_product_auth_builduploader_client(upload_build_client):
    r = upload_build_client.patch('/products/test', {'foo': 'bar'})
    assert r.status == 403


def test_patch_product_auth_builddeprecator_client(upload_build_client):
    r = upload_build_client.patch('/products/test', {'foo': 'bar'})
    assert r.status == 403


# Authorizion tests: POST /products/<slug>/dashboard =========================
# Only the full admin client and the product-authorized client should get in


def test_post_dashboard_auth_anon(anon_client):
    r = anon_client.post('/products/test/dashboard', {})
    assert r.status == 401


def test_post_dashboard_auth_product_client(product_client):
    with pytest.raises(NotFound):
        product_client.post('/products/test/dashboard', {})


def test_post_dashboard_auth_edition_client(edition_client):
    r = edition_client.post('/products/test/dashboard', {})
    assert r.status == 403


def test_post_dashboard_auth_builduploader_client(upload_build_client):
    r = upload_build_client.post('/products/test/dashboard', {})
    assert r.status == 403
