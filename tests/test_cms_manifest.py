# tests/test_cms_manifest.py
# Endpoint tests + invariant: every site_config-backed manifest field
# must exist as a key in DEFAULT_CONFIG (catches drift between manifest and seed).

import pytest
from app.routes.site_config import DEFAULT_CONFIG


def _config_keys():
    return {cfg['key'] for cfg in DEFAULT_CONFIG}


def test_manifest_home_returns_200(client):
    res = client.get('/api/cms/manifest/home')
    assert res.status_code == 200
    body = res.get_json()
    assert body['page_slug']    == 'home'
    assert body['page_title']   == 'Homepage'
    assert body['preview_path'] == '/'
    assert isinstance(body['sections'], list) and len(body['sections']) >= 1


def test_manifest_about_returns_200(client):
    res = client.get('/api/cms/manifest/about')
    assert res.status_code == 200
    assert res.get_json()['page_slug'] == 'about'


def test_manifest_programs_returns_200(client):
    res = client.get('/api/cms/manifest/programs')
    assert res.status_code == 200
    assert res.get_json()['page_slug'] == 'programs'


def test_manifest_unknown_returns_404(client):
    res = client.get('/api/cms/manifest/does-not-exist')
    assert res.status_code == 404


@pytest.mark.parametrize('slug', ['home', 'about', 'programs'])
def test_every_site_config_field_key_exists_in_seed(client, slug):
    """Drift guard: every manifest field with kind='site_config' references a key in DEFAULT_CONFIG."""
    res = client.get(f'/api/cms/manifest/{slug}')
    assert res.status_code == 200
    body = res.get_json()
    cfg_keys = _config_keys()
    for section in body['sections']:
        for field in section['fields']:
            if field['kind'] == 'site_config':
                assert field['key'] in cfg_keys, \
                    f"manifest {slug} references missing site_config key {field['key']!r}"
