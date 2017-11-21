"""Test an Edition that tracks LSST document releases (``lsst_doc).
"""


def test_lsst_doc_edition(client):
    """Test an edition that tracks LSST Doc semantic versions.

    1. Create a build on `master`; it should be tracked because the LSST_DOC
       mode tracks master if a semantic version tag hasn't been pushed yet.
    2. Create a ticket branch; it isn't tracked.
    3. Create a v1.0 build; it is tracked.
    4. Create another build on `master`; it isn't tracked because we already
       have the v1.0 build.
    5. Create a v0.9 build that is not tracked because it's older.
    6. Create a v1.1 build that **is** tracked because it's newer.
    """
    # Add product
    p1_data = {
        'slug': 'ldm-151',
        'doc_repo': 'https://github.com/lsst/LDM-151',
        'main_mode': 'lsst_doc',
        'title': 'Applications Design',
        'root_domain': 'lsst.io',
        'root_fastly_domain': 'global.ssl.fastly.net',
        'bucket_name': 'bucket-name'
    }
    r = client.post('/products/', p1_data)
    assert r.status == 201
    # p1_url = r.headers['Location']

    # Get the URL for the default edition
    r = client.get('/products/ldm-151/editions/')
    edition_url = r.json['editions'][0]

    # Create a build on 'master'
    b1_data = {
        'slug': 'b1',
        'github_requester': 'jonathansick',
        'git_refs': ['master']
    }
    r = client.post('/products/ldm-151/builds/', b1_data)
    b1_url = r.headers['Location']
    r = client.patch(b1_url, {'uploaded': True})

    # Test that the main edition updated because there are no builds yet
    # with semantic versions
    r = client.get(edition_url)
    assert r.json['build_url'] == b1_url

    # Create a ticket branch build
    b2_data = {
        'slug': 'b2',
        'github_requester': 'jonathansick',
        'git_refs': ['tickets/DM-1']
    }
    r = client.post('/products/ldm-151/builds/', b2_data)
    b2_url = r.headers['Location']
    r = client.patch(b2_url, {'uploaded': True})

    # Test that the main edition *did not* update because this build is
    # neither for master not a semantic version.
    # with semantic versions
    r = client.get(edition_url)
    assert r.json['build_url'] == b1_url

    # Create a build with a semantic version tag.
    b3_data = {
        'slug': 'b3',
        'github_requester': 'jonathansick',
        'git_refs': ['v1.0']
    }
    r = client.post('/products/ldm-151/builds/', b3_data)
    b3_url = r.headers['Location']
    r = client.patch(b3_url, {'uploaded': True})

    # Test that the main edition updated
    r = client.get(edition_url)
    assert r.json['build_url'] == b3_url

    # Create another build on 'master'
    b4_data = {
        'slug': 'b4',
        'github_requester': 'jonathansick',
        'git_refs': ['master']
    }
    r = client.post('/products/ldm-151/builds/', b4_data)
    b4_url = r.headers['Location']
    r = client.patch(b4_url, {'uploaded': True})

    # Test that the main edition *did not* update because now it's sticking
    # to only show semantic versions.
    r = client.get(edition_url)
    assert r.json['build_url'] == b3_url

    # Create a build with a **older** semantic version tag.
    b5_data = {
        'slug': 'b5',
        'github_requester': 'jonathansick',
        'git_refs': ['v0.9']
    }
    r = client.post('/products/ldm-151/builds/', b5_data)
    b5_url = r.headers['Location']
    r = client.patch(b5_url, {'uploaded': True})

    # Test that the main edition *did not* update b/c it's older
    r = client.get(edition_url)
    assert r.json['build_url'] == b3_url

    # Create a build with a **newer** semantic version tag.
    b6_data = {
        'slug': 'b6',
        'github_requester': 'jonathansick',
        'git_refs': ['v1.1']
    }
    r = client.post('/products/ldm-151/builds/', b6_data)
    b6_url = r.headers['Location']
    r = client.patch(b6_url, {'uploaded': True})

    # Test that the main edition updated
    r = client.get(edition_url)
    assert r.json['build_url'] == b6_url
