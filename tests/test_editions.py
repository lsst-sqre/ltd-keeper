"""Tests for the editions API."""

import pytest
from werkzeug.exceptions import NotFound


def test_editions(client):
    # Add a sample product
    p = {'slug': 'pipelines',
         'doc_repo': 'https://github.com/lsst/pipelines_docs.git',
         'title': 'LSST Science Pipelines',
         'root_domain': 'lsst.io',
         'root_fastly_domain': 'global.ssl.fastly.net',
         'bucket_name': 'bucket-name'}
    r = client.post('/products/', p)
    product_url = r.headers['Location']
    assert r.status == 201

    # Create builds
    r = client.post('/products/pipelines/builds/',
                    {'git_refs': ['master']})
    assert r.status == 201
    b1_url = r.json['self_url']
    client.patch(b1_url, {'uploaded': True})

    r = client.post('/products/pipelines/builds/',
                    {'git_refs': ['master']})
    assert r.status == 201
    b2_url = r.json['self_url']
    client.patch(b2_url, {'uploaded': True})

    # Setup an edition
    e1 = {'tracked_refs': ['master'],
          'slug': 'latest',
          'title': 'Latest',
          'build_url': b1_url}
    r = client.post(product_url + '/editions/', e1)
    e1_url = r.headers['Location']

    r = client.get(e1_url)
    assert r.status == 200
    assert r.json['tracked_refs'][0] == e1['tracked_refs'][0]
    assert r.json['slug'] == e1['slug']
    assert r.json['title'] == e1['title']
    assert r.json['build_url'] == b1_url
    assert r.json['date_created'] is not None
    assert r.json['date_ended'] is None
    assert r.json['published_url'] == 'https://pipelines.lsst.io/v/latest'

    # Re-build the edition
    r = client.patch(e1_url, {'build_url': b2_url})
    assert r.status == 200
    assert r.json['build_url'] == b2_url

    # Change the title with PATCH
    r = client.patch(e1_url, {'title': "Development version"})
    assert r.status == 200
    assert r.json['title'] == 'Development version'

    # Change the tracked_refs with PATCH
    r = client.patch(e1_url, {'tracked_refs': ['tickets/DM-9999', 'master']})
    assert r.status == 200
    assert r.json['tracked_refs'][0] == 'tickets/DM-9999'
    assert r.json['tracked_refs'][1] == 'master'

    # Deprecate the editon
    r = client.delete(e1_url)
    assert r.status == 200

    r = client.get(e1_url)
    assert r.status == 200
    assert r.json['date_ended'] is not None

    # Deprecated editions no longer in the editions list
    r = client.get(product_url + '/editions/')
    assert r.status == 200
    assert len(r.json['editions']) == 0


# Authorizion tests: POST /products/<slug>/editions/ =========================
# Only the full admin client and the edition-authorized client should get in


def test_post_edition_auth_anon(anon_client):
    r = anon_client.post('/products/test/editions/', {'foo': 'bar'})
    assert r.status == 401


def test_post_edition_auth_product_client(product_client):
    r = product_client.post('/products/test/editions/', {'foo': 'bar'})
    assert r.status == 403


def test_post_edition_auth_edition_client(edition_client):
    with pytest.raises(NotFound):
        edition_client.post('/products/test/editions/', {'foo': 'bar'})


def test_post_edition_auth_builduploader_client(upload_build_client):
    r = upload_build_client.post('/products/test/editions/', {'foo': 'bar'})
    assert r.status == 403


def test_post_edition_auth_builddeprecator_client(deprecate_build_client):
    r = deprecate_build_client.post('/products/test/editions/', {'foo': 'bar'})
    assert r.status == 403


# Authorizion tests: PATCH /editions/<slug>/editions/ =========================
# Only the full admin client and the edition-authorized client should get in


def test_patch_edition_auth_anon(anon_client):
    r = anon_client.patch('/editions/1', {'foo': 'bar'})
    assert r.status == 401


def test_patch_edition_auth_product_client(product_client):
    r = product_client.patch('/editions/1', {'foo': 'bar'})
    assert r.status == 403


def test_patch_edition_auth_edition_client(edition_client):
    with pytest.raises(NotFound):
        edition_client.patch('/editions/1', {'foo': 'bar'})


def test_patch_edition_auth_builduploader_client(upload_build_client):
    r = upload_build_client.patch('/editions/1', {'foo': 'bar'})
    assert r.status == 403


def test_patch_edition_auth_builddeprecator_client(deprecate_build_client):
    r = deprecate_build_client.patch('/editions/1', {'foo': 'bar'})
    assert r.status == 403


# Authorizion tests: DELETE /editions/<slug> =================================
# Only the full admin client and the edition-authorized client should get in


def test_delete_edition_auth_anon(anon_client):
    r = anon_client.delete('/editions/1')
    assert r.status == 401


def test_delete_edition_auth_product_client(product_client):
    r = product_client.delete('/editions/1')
    assert r.status == 403


def test_delete_edition_auth_edition_client(edition_client):
    with pytest.raises(NotFound):
        edition_client.delete('/editions/1')


def test_delete_edition_auth_builduploader_client(upload_build_client):
    r = upload_build_client.delete('/editions/1')
    assert r.status == 403


def test_delete_edition_auth_builddeprecator_client(deprecate_build_client):
    r = deprecate_build_client.delete('/editions/1')
    assert r.status == 403
