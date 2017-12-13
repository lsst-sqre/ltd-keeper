"""Tests for PATCHing an edition to change the tracking mode from
``git_refs`` to ``lsst_doc``.
"""


def test_pach_lsst_doc_edition(client):
    """Test patching an edition from tracking a Git ref to an LSST doc.

    1. Create a product with the default GIT_REF tracking mode for the
       main edition.
    2. Post a build on `master`; it is tracked.
    3. Post a `v1.0` build; it is not tracked.
    4. Patch the main edition to use the LSST_DOC tracking mode.
    5. Post a `v1.1` build that is tracked.
    """
    # Add product
    p1_data = {
        'slug': 'ldm-151',
        'doc_repo': 'https://github.com/lsst/LDM-151',
        'main_mode': 'git_refs',  # default
        'title': 'Applications Design',
        'root_domain': 'lsst.io',
        'root_fastly_domain': 'global.ssl.fastly.net',
        'bucket_name': 'bucket-name'
    }
    r = client.post('/products/', p1_data)
    assert r.status == 201

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
    # Test that the main edition updated.
    r = client.get(edition_url)
    assert r.json['build_url'] == b1_url

    # Create a build with a semantic version tag.
    b2_data = {
        'slug': 'b2',
        'github_requester': 'jonathansick',
        'git_refs': ['v1.0']
    }
    r = client.post('/products/ldm-151/builds/', b2_data)
    b2_url = r.headers['Location']
    r = client.patch(b2_url, {'uploaded': True})
    # Test that the main edition *did not* update
    r = client.get(edition_url)
    assert r.json['build_url'] == b1_url

    # PATCH the tracking mode of the edition
    edition_patch_data = {
        'mode': 'lsst_doc'
    }
    r = client.patch(edition_url, edition_patch_data)
    assert r.status == 200

    # Create another build with a semantic version tag.
    b3_data = {
        'slug': 'b3',
        'github_requester': 'jonathansick',
        'git_refs': ['v1.1']
    }
    r = client.post('/products/ldm-151/builds/', b3_data)
    b3_url = r.headers['Location']
    r = client.patch(b3_url, {'uploaded': True})
    # Test that the main edition *did* update now
    r = client.get(edition_url)
    assert r.json['build_url'] == b3_url
