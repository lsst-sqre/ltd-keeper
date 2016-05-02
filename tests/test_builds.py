"""Tests for the builds API."""

import pytest
from werkzeug.exceptions import NotFound
from app.exceptions import ValidationError


def test_builds(client):
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

    # Add a sample edition
    e = {'tracked_refs': ['master'],
         'slug': 'latest',
         'title': 'Latest',
         'published_url': 'pipelines.lsst.io'}
    r = client.post(product_url + '/editions/', e)
    edition_url = r.headers['Location']

    # Initially no builds
    r = client.get('/products/pipelines/builds/')
    assert r.status == 200
    assert len(r.json['builds']) == 0

    # Add a build
    b1 = {'slug': 'b1',
          'github_requester': 'jonathansick',
          'git_refs': ['master']}
    r = client.post('/products/pipelines/builds/', b1)
    assert r.status == 201
    assert r.json['product_url'] == product_url
    assert r.json['slug'] == b1['slug']
    assert r.json['date_created'] is not None
    assert r.json['date_ended'] is None
    assert r.json['uploaded'] is False
    assert r.json['published_url'] == 'https://pipelines.lsst.io/builds/b1'
    assert len(r.json['surrogate_key']) == 32  # should be a uuid4 -> hex
    build_url = r.headers['Location']

    # Re-add build with same slug; should fail
    with pytest.raises(ValidationError):
        r = client.post('/products/pipelines/builds/', b1)

    # List builds
    r = client.get('/products/pipelines/builds/')
    assert r.status == 200
    assert len(r.json['builds']) == 1

    # Get build
    r = client.get('/builds/1')
    assert r.status == 200
    assert r.json['bucket_name'] == 'bucket-name'
    assert r.json['bucket_root_dir'] == 'pipelines/builds/b1'

    # Register upload
    r = client.patch('/builds/1', {'uploaded': True})
    assert r.status == 200

    r = client.get('/builds/1')
    assert r.json['uploaded'] is True

    # Check that the edition was rebuilt
    edition_data = client.get(edition_url)
    assert edition_data.json['build_url'] == build_url

    # Deprecate build
    r = client.delete('/builds/1')
    assert r.status == 200

    r = client.get('/builds/1')
    assert r.json['product_url'] == product_url
    assert r.json['slug'] == b1['slug']
    assert r.json['date_created'] is not None
    assert r.json['date_ended'] is not None

    # Build no longer in listing
    r = client.get('/products/pipelines/builds/')
    assert r.status == 200
    assert len(r.json['builds']) == 0

    # Add some auto-slugged builds
    b2 = {'git_refs': ['master']}
    r = client.post('/products/pipelines/builds/', b2)
    assert r.status == 201
    assert r.json['slug'] == '1'

    b3 = {'git_refs': ['master']}
    r = client.post('/products/pipelines/builds/', b3)
    assert r.status == 201
    assert r.json['slug'] == '2'

    # Add a build missing 'git_refs'
    b4 = {'slug': 'bad-build'}
    with pytest.raises(ValidationError):
        r = client.post('/products/pipelines/builds/', b4)

    # Add a build with a badly formatted git_refs
    b5 = {'slug': 'another-bad-build',
          'git_refs': 'master'}
    with pytest.raises(ValidationError):
        r = client.post('/products/pipelines/builds/', b5)

    # Add a build and see if an edition was automatically created
    b6 = {'git_refs': ['tickets/DM-1234']}
    r = client.post('/products/pipelines/builds/', b6)
    assert r.status == 201
    r = client.get('/products/pipelines/editions/')
    assert len(r.json['editions']) == 3
    auto_edition_url = r.json['editions'][-1]
    r = client.get(auto_edition_url)
    assert r.json['slug'] == 'DM-1234'


# Authorizion tests: POST /products/<slug>/builds/ ===========================
# Only the build-upload auth'd client should get in


def test_post_build_auth_anon(anon_client):
    r = anon_client.post('/products/test/builds/', {'foo': 'bar'})
    assert r.status == 401


def test_post_build_auth_product_client(product_client):
    r = product_client.post('/products/test/builds/', {'foo': 'bar'})
    assert r.status == 403


def test_post_build_auth_edition_client(edition_client):
    r = edition_client.post('/products/test/builds/', {'foo': 'bar'})
    assert r.status == 403


def test_post_build_auth_builduploader_client(upload_build_client):
    with pytest.raises(NotFound):
        upload_build_client.post('/products/test/builds/', {'foo': 'bar'})


def test_post_build_auth_builddeprecator_client(deprecate_build_client):
    r = deprecate_build_client.post('/products/test/builds/', {'foo': 'bar'})
    assert r.status == 403


# Authorizion tests: PATCH /products/<slug>/builds/ ==========================
# Only the build-upload auth'd client should get in


def test_patch_build_auth_anon(anon_client):
    r = anon_client.patch('/builds/1', {'foo': 'bar'})
    assert r.status == 401


def test_patch_build_auth_product_client(product_client):
    r = product_client.patch('/builds/1', {'foo': 'bar'})
    assert r.status == 403


def test_patch_build_auth_edition_client(edition_client):
    r = edition_client.patch('/builds/1', {'foo': 'bar'})
    assert r.status == 403


def test_patch_build_auth_builduploader_client(upload_build_client):
    with pytest.raises(NotFound):
        upload_build_client.patch('/builds/1', {'foo': 'bar'})


def test_patch_build_auth_builddeprecator_client(deprecate_build_client):
    r = deprecate_build_client.patch('/builds/1', {'foo': 'bar'})
    assert r.status == 403


# Authorizion tests: DELETE /products/<slug>/builds/ =========================
# Only the build-deprecator auth'd client should get in


def test_delete_build_auth_anon(anon_client):
    r = anon_client.delete('/builds/1')
    assert r.status == 401


def test_delete_build_auth_product_client(product_client):
    r = product_client.delete('/builds/1')
    assert r.status == 403


def test_delete_build_auth_edition_client(edition_client):
    r = edition_client.delete('/builds/1')
    assert r.status == 403


def test_delete_build_auth_builduploader_client(upload_build_client):
    r = upload_build_client.delete('/builds/1')
    assert r.status == 403


def test_delete_build_auth_builddeprecator_client(deprecate_build_client):
    with pytest.raises(NotFound):
        deprecate_build_client.delete('/builds/1', {'foo': 'bar'})
