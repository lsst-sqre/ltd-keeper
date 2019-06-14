"""Test an Edition that tracks LSST document releases (``lsst_doc).
"""

from keeper.tasks.dashboardbuild import build_dashboard
from keeper.tasks.editionrebuild import rebuild_edition


def test_lsst_doc_edition(client, mocker):
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
    mocked_product_append_task = mocker.patch(
        'keeper.api.products.append_task_to_chain')
    mocked_product_launch_chain = mocker.patch(
        'keeper.api.products.launch_task_chain')
    mocked_build_append_task = mocker.patch(
        'keeper.api.builds.append_task_to_chain')
    mocked_build_launch_chain = mocker.patch(
        'keeper.api.builds.launch_task_chain')
    mocked_models_append_task = mocker.patch(
        'keeper.models.append_task_to_chain')
    # These mocks are needed but not checked
    mocker.patch('keeper.api.editions.append_task_to_chain')
    mocker.patch('keeper.api.editions.launch_task_chain')

    # ========================================================================
    # Add product /products/ldm-151
    mocker.resetall()

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
    p1_url = r.headers['Location']

    assert r.status == 201
    mocked_product_append_task.assert_called_with(
        build_dashboard.si(p1_url)
    )
    mocked_product_launch_chain.assert_called_once()

    # ========================================================================
    # Get the URL for the default edition
    r = client.get(p1_url + '/editions/')
    edition_url = r.json['editions'][0]
    print("Editions")
    print(r.json['editions'])

    # ========================================================================
    # Create a build on 'master'
    mocker.resetall()

    b1_data = {
        'slug': 'b1',
        'github_requester': 'jonathansick',
        'git_refs': ['master']
    }
    r = client.post('/products/ldm-151/builds/', b1_data)
    b1_url = r.headers['Location']

    mocked_build_launch_chain.assert_called_once()

    # ========================================================================
    # Confirm build on 'master'
    mocker.resetall()

    r = client.patch(b1_url, {'uploaded': True})

    mocked_models_append_task.assert_any_call(
        rebuild_edition.si('http://example.test/editions/1', 1)
    )

    # The 'master' edition was also automatically created to track master.
    mocked_models_append_task.assert_any_call(
        rebuild_edition.si('http://example.test/editions/2', 2)
    )

    # Manually reset pending_rebuild (the rebuild_edition task would have
    # done this automatically)
    r = client.get(edition_url)
    assert r.json['pending_rebuild'] is True
    r = client.patch(edition_url, {'pending_rebuild': False})

    # And for the master edition
    r = client.get('http://example.test/editions/2')
    assert r.json['pending_rebuild'] is True
    r = client.patch('http://example.test/editions/2',
                     {'pending_rebuild': False})

    # Test that the main edition updated because there are no builds yet
    # with semantic versions
    r = client.get(edition_url)
    assert r.json['build_url'] == b1_url
    assert r.json['pending_rebuild'] is False

    # ========================================================================
    # Create a ticket branch build
    mocker.resetall()

    b2_data = {
        'slug': 'b2',
        'github_requester': 'jonathansick',
        'git_refs': ['tickets/DM-1']
    }
    r = client.post('/products/ldm-151/builds/', b2_data)
    b2_url = r.headers['Location']

    mocked_build_launch_chain.assert_called_once()

    # ========================================================================
    # Confirm ticket branch build
    mocker.resetall()

    r = client.patch(b2_url, {'uploaded': True})

    mocked_models_append_task.assert_called_with(
        rebuild_edition.si('http://example.test/editions/3', 3)
    )
    mocked_build_launch_chain.assert_called_once()

    # Test that the main edition *did not* update because this build is
    # neither for master not a semantic version.
    # with semantic versions
    r = client.get(edition_url)
    assert r.json['build_url'] == b1_url

    # ========================================================================
    # Create a build with a semantic version tag.
    mocker.resetall()

    b3_data = {
        'slug': 'b3',
        'github_requester': 'jonathansick',
        'git_refs': ['v1.0']
    }
    r = client.post('/products/ldm-151/builds/', b3_data)
    b3_url = r.headers['Location']

    mocked_build_append_task.assert_called_with(
        build_dashboard.si(p1_url)
    )
    mocked_build_launch_chain.assert_called_once()
    mocked_build_launch_chain.reset_mock()

    # ========================================================================
    # Confirm v1.0 build
    mocker.resetall()

    r = client.patch(b3_url, {'uploaded': True})

    mocked_build_append_task.assert_called_with(
        build_dashboard.si(p1_url)
    )
    mocked_build_launch_chain.assert_called_once()
    mocked_build_launch_chain.reset_mock()
    # Rebuilds for the main and v1-0 editions were triggered
    mocked_models_append_task.assert_any_call(
        rebuild_edition.si('http://example.test/editions/1', 1))
    mocked_models_append_task.assert_any_call(
        rebuild_edition.si('http://example.test/editions/4', 4))

    # Test that the main edition updated
    r = client.get(edition_url)
    assert r.json['build_url'] == b3_url
    assert r.json['pending_rebuild'] is True

    # Test that the v1-0 edition updated
    r = client.get('http://example.test/editions/4')
    assert r.json['build_url'] == b3_url
    assert r.json['pending_rebuild'] is True

    # Manually reset the pending_rebuild semaphores
    r = client.patch(edition_url, {'pending_rebuild': False})
    r = client.patch(
        'http://example.test/editions/4',
        {'pending_rebuild': False})

    # ========================================================================
    # Create another build on 'master'
    mocker.resetall()

    b4_data = {
        'slug': 'b4',
        'github_requester': 'jonathansick',
        'git_refs': ['master']
    }
    r = client.post('/products/ldm-151/builds/', b4_data)
    b4_url = r.headers['Location']

    # ========================================================================
    # Confirm master build
    mocker.resetall()

    r = client.patch(b4_url, {'uploaded': True})

    # Test that the main edition *did not* update because now it's sticking
    # to only show semantic versions.
    r = client.get(edition_url)
    assert r.json['build_url'] == b3_url

    # ========================================================================
    # Create a build with a **older** semantic version tag.
    mocker.resetall()

    b5_data = {
        'slug': 'b5',
        'github_requester': 'jonathansick',
        'git_refs': ['v0.9']
    }
    r = client.post('/products/ldm-151/builds/', b5_data)
    b5_url = r.headers['Location']

    # ========================================================================
    # Confirm v0.9 build
    mocker.resetall()

    r = client.patch(b5_url, {'uploaded': True})

    # Test that the main edition *did not* update b/c it's older
    r = client.get(edition_url)
    assert r.json['build_url'] == b3_url

    # ========================================================================
    # Create a build with a **newer** semantic version tag.
    mocker.resetall()

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

    # Rebuilds for the main and v1-0 editions were triggered
    mocked_models_append_task.assert_any_call(
        rebuild_edition.si('http://example.test/editions/1', 1))
    mocked_models_append_task.assert_any_call(
        rebuild_edition.si('http://example.test/editions/6', 6))

    # Manually reset the pending_rebuild semaphores
    r = client.patch(edition_url, {'pending_rebuild': False})
    r = client.patch(
        'http://example.test/editions/6',
        {'pending_rebuild': False})
