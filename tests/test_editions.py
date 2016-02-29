"""Tests for the editions API."""


def test_editions(client):
    # Add a sample product
    p = {'slug': 'lsst_apps',
         'doc_repo': 'https://github.com/lsst/pipelines_docs.git',
         'title': 'LSST Science Pipelines',
         'domain': 'pipelines.lsst.io',
         'bucket_name': 'bucket-name'}
    r = client.post('/products/', p)
    product_url = r.headers['Location']
    assert r.status == 201

    # Create builds
    r = client.post('/products/lsst_apps/builds/',
                    {'git_refs': ['master']})
    assert r.status == 201
    b1_url = r.json['self_url']

    r = client.post('/products/lsst_apps/builds/',
                    {'git_refs': ['master']})
    assert r.status == 201
    b2_url = r.json['self_url']

    # Setup an edition
    e1 = {'tracked_refs': ['master'],
          'slug': 'latest',
          'title': 'Latest',
          'published_url': 'pipelines.lsst.io',
          'build_url': b1_url}
    r = client.post(product_url + '/editions/', e1)
    e1_url = r.headers['Location']

    r = client.get(e1_url)
    assert r.status == 200
    assert r.json['tracked_refs'][0] == e1['tracked_refs'][0]
    assert r.json['slug'] == e1['slug']
    assert r.json['title'] == e1['title']
    assert r.json['published_url'] == e1['published_url']
    assert r.json['build_url'] == b1_url
    assert r.json['date_created'] is not None
    assert r.json['date_ended'] is None

    # Re-build the edition
    r = client.post(e1_url + '/rebuild', {'build_url': b2_url})
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
