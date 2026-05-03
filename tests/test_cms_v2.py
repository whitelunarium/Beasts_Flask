# tests/test_cms_v2.py
# Coverage for the v2 CMS API: sections registry, page read, draft patch ops,
# render API, publish, preview tokens.

import json
from datetime import datetime, timedelta

import pytest

from app import db
from app.models.page_template import PageTemplate, STATE_DRAFT, STATE_PUBLISHED
from app.models.preview_token import PreviewToken
from app.models.user import User


# ── Sections registry ────────────────────────────────────────────────────────

def test_registry_lists_starter_sections(client):
    res = client.get('/api/cms/sections-registry')
    assert res.status_code == 200
    body = res.get_json()
    types = {s['type'] for s in body['sections']}
    assert {'hero', 'text_block', 'image_with_text', 'faq'}.issubset(types)
    # Each schema has the minimum fields
    for s in body['sections']:
        assert 'type' in s
        assert 'label' in s
        assert isinstance(s.get('settings'), list)


def test_faq_section_supports_blocks_end_to_end(client, app):
    _login_admin(client, app)
    # Add FAQ section
    res = client.patch('/api/cms/page/home/draft', json={
        'patches': [{'op': 'add', 'type': 'faq'}]
    }).get_json()
    sid = res['template']['order'][0]
    # Add three Q&A blocks
    res = client.patch('/api/cms/page/home/draft', json={
        'patches': [
            {'op': 'add_block', 'sid': sid, 'block_type': 'qa',
             'settings': {'question': 'Q1?', 'answer': 'A1'}},
            {'op': 'add_block', 'sid': sid, 'block_type': 'qa',
             'settings': {'question': 'Q2?', 'answer': 'A2'}},
            {'op': 'add_block', 'sid': sid, 'block_type': 'qa',
             'settings': {'question': 'Q3?', 'answer': 'A3'}},
        ]
    }).get_json()
    section = res['template']['sections'][sid]
    assert len(section['block_order']) == 3
    # Rendered HTML should contain all three questions
    html = res['sections_html'][sid]
    assert 'Q1?' in html and 'Q2?' in html and 'Q3?' in html


def test_faq_block_reorder(client, app):
    _login_admin(client, app)
    a = client.patch('/api/cms/page/home/draft', json={
        'patches': [{'op': 'add', 'type': 'faq'}]
    }).get_json()
    sid = a['template']['order'][0]
    add_blocks = client.patch('/api/cms/page/home/draft', json={
        'patches': [
            {'op': 'add_block', 'sid': sid, 'block_type': 'qa', 'settings': {'question': 'A'}},
            {'op': 'add_block', 'sid': sid, 'block_type': 'qa', 'settings': {'question': 'B'}},
        ]
    }).get_json()
    block_order = add_blocks['template']['sections'][sid]['block_order']
    assert len(block_order) == 2
    # Reverse the order
    reversed_order = list(reversed(block_order))
    res = client.patch('/api/cms/page/home/draft', json={
        'patches': [{'op': 'reorder_blocks', 'sid': sid, 'block_order': reversed_order}]
    }).get_json()
    assert res['template']['sections'][sid]['block_order'] == reversed_order


def test_registry_drift_guard_each_section_has_settings_list(client):
    res = client.get('/api/cms/sections-registry')
    body = res.get_json()
    for s in body['sections']:
        for field in s['settings']:
            assert 'id' in field, f"{s['type']} field missing id"
            assert 'type' in field, f"{s['type']} field missing type"


# ── Page read (empty state is OK) ────────────────────────────────────────────

def test_get_page_returns_empty_when_no_template(client):
    res = client.get('/api/cms/page/home')
    assert res.status_code == 200
    body = res.get_json()
    assert body['page_slug'] == 'home'
    assert body['state'] == 'published'
    assert body['template'] == {'sections': {}, 'order': []}
    assert body['sections_html'] == {}


def test_get_page_invalid_state_400(client):
    res = client.get('/api/cms/page/home?state=bogus')
    assert res.status_code == 400


def test_get_page_draft_unauthorized_without_admin_or_token(client):
    res = client.get('/api/cms/page/home?state=draft')
    assert res.status_code == 401


# ── Helpers for admin client ─────────────────────────────────────────────────

def _login_admin(client, app):
    """Sign in as the seeded admin via flask-login session_transaction."""
    with app.app_context():
        admin = User.query.filter_by(role='admin').first()
        assert admin is not None, "conftest should seed an admin"
        admin_id = admin.id
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_id)
        sess['_fresh'] = True
    return admin_id


# ── Patches: add / set / reorder / remove ────────────────────────────────────

def test_admin_can_add_a_hero_section(client, app):
    _login_admin(client, app)
    res = client.patch('/api/cms/page/home/draft', json={
        'patches': [{'op': 'add', 'type': 'hero'}]
    })
    assert res.status_code == 200, res.get_json()
    body = res.get_json()
    assert len(body['template']['order']) == 1
    sid = body['template']['order'][0]
    assert body['template']['sections'][sid]['type'] == 'hero'
    # Default settings filled in from schema
    assert body['template']['sections'][sid]['settings']['headline'] == 'Neighbors Helping Neighbors'
    # Affected sids include the new section
    assert sid in body['affected_sids']
    # Rendered HTML returned for the affected section, and it contains the headline
    assert 'cms-section-' + sid in body['sections_html'][sid]
    assert 'Neighbors Helping Neighbors' in body['sections_html'][sid]


def test_admin_can_update_a_setting_via_set_op(client, app):
    _login_admin(client, app)
    add = client.patch('/api/cms/page/home/draft', json={
        'patches': [{'op': 'add', 'type': 'hero'}]
    }).get_json()
    sid = add['template']['order'][0]
    res = client.patch('/api/cms/page/home/draft', json={
        'patches': [{'op': 'set', 'sid': sid, 'key': 'headline', 'value': 'Custom headline'}]
    })
    assert res.status_code == 200
    body = res.get_json()
    assert body['template']['sections'][sid]['settings']['headline'] == 'Custom headline'
    assert 'Custom headline' in body['sections_html'][sid]


def test_admin_can_reorder_sections(client, app):
    _login_admin(client, app)
    a = client.patch('/api/cms/page/home/draft', json={
        'patches': [{'op': 'add', 'type': 'hero'}, {'op': 'add', 'type': 'text_block'}]
    }).get_json()
    sid_a, sid_b = a['template']['order']
    r = client.patch('/api/cms/page/home/draft', json={
        'patches': [{'op': 'reorder', 'order': [sid_b, sid_a]}]
    })
    assert r.status_code == 200
    assert r.get_json()['template']['order'] == [sid_b, sid_a]


def test_admin_can_remove_a_section(client, app):
    _login_admin(client, app)
    a = client.patch('/api/cms/page/home/draft', json={
        'patches': [{'op': 'add', 'type': 'hero'}, {'op': 'add', 'type': 'text_block'}]
    }).get_json()
    sid_a, sid_b = a['template']['order']
    r = client.patch('/api/cms/page/home/draft', json={
        'patches': [{'op': 'remove', 'sid': sid_a}]
    })
    assert r.status_code == 200
    body = r.get_json()
    assert sid_a not in body['template']['sections']
    assert body['template']['order'] == [sid_b]


def test_admin_can_duplicate_a_section(client, app):
    _login_admin(client, app)
    a = client.patch('/api/cms/page/home/draft', json={
        'patches': [{'op': 'add', 'type': 'hero',
                     'settings': {'headline': 'Original', 'sub_headline': 'sub',
                                  'cta_label': 'go', 'cta_url': '#',
                                  'text_alignment': 'center'}}]
    }).get_json()
    sid = a['template']['order'][0]
    r = client.patch('/api/cms/page/home/draft', json={
        'patches': [{'op': 'duplicate', 'sid': sid}]
    })
    assert r.status_code == 200
    body = r.get_json()
    assert len(body['template']['order']) == 2
    new_sid = body['template']['order'][1]
    assert new_sid != sid
    # Same settings
    assert (body['template']['sections'][new_sid]['settings']['headline']
            == body['template']['sections'][sid]['settings']['headline']
            == 'Original')


def test_admin_can_toggle_visibility(client, app):
    _login_admin(client, app)
    a = client.patch('/api/cms/page/home/draft', json={
        'patches': [{'op': 'add', 'type': 'hero'}]
    }).get_json()
    sid = a['template']['order'][0]
    r = client.patch('/api/cms/page/home/draft', json={
        'patches': [{'op': 'visibility', 'sid': sid, 'visible': False}]
    })
    assert r.status_code == 200
    assert r.get_json()['template']['sections'][sid]['visible'] is False


def test_unknown_op_400(client, app):
    _login_admin(client, app)
    r = client.patch('/api/cms/page/home/draft', json={
        'patches': [{'op': 'sabotage'}]
    })
    assert r.status_code == 400


def test_add_with_unknown_type_400(client, app):
    _login_admin(client, app)
    r = client.patch('/api/cms/page/home/draft', json={
        'patches': [{'op': 'add', 'type': 'made_up_type'}]
    })
    assert r.status_code == 400


# ── Publish ──────────────────────────────────────────────────────────────────

def test_publish_copies_draft_to_published(client, app):
    _login_admin(client, app)
    client.patch('/api/cms/page/home/draft', json={
        'patches': [{'op': 'add', 'type': 'hero'}]
    })
    res = client.post('/api/cms/page/home/publish')
    assert res.status_code == 200, res.get_json()
    body = res.get_json()
    assert body['page_slug'] == 'home'
    # Now the published-state read should return the same template
    pub = client.get('/api/cms/page/home').get_json()
    assert pub['state'] == 'published'
    assert len(pub['template']['order']) == 1


def test_publish_is_idempotent(client, app):
    _login_admin(client, app)
    client.patch('/api/cms/page/home/draft', json={
        'patches': [{'op': 'add', 'type': 'hero'}]
    })
    r1 = client.post('/api/cms/page/home/publish')
    r2 = client.post('/api/cms/page/home/publish')
    assert r1.status_code == 200
    assert r2.status_code == 200


def test_publish_404_when_no_draft(client, app):
    _login_admin(client, app)
    r = client.post('/api/cms/page/no-such-page/publish')
    assert r.status_code == 404


# ── Render API ───────────────────────────────────────────────────────────────

def test_render_one_section(client, app):
    _login_admin(client, app)
    a = client.patch('/api/cms/page/home/draft', json={
        'patches': [{'op': 'add', 'type': 'hero'}]
    }).get_json()
    sid = a['template']['order'][0]
    # Admin can render draft
    r = client.get(f'/api/cms/render?page=home&section={sid}&state=draft')
    assert r.status_code == 200
    body = r.get_json()
    assert body['section_id'] == sid
    assert body['section_type'] == 'hero'
    assert f'cms-section-{sid}' in body['html']


def test_render_404_for_missing_section(client, app):
    _login_admin(client, app)
    client.patch('/api/cms/page/home/draft', json={
        'patches': [{'op': 'add', 'type': 'hero'}]
    })
    r = client.get('/api/cms/render?page=home&section=does-not-exist&state=draft')
    assert r.status_code == 404


def test_render_validation_400_when_params_missing(client):
    r = client.get('/api/cms/render')
    assert r.status_code == 400


# ── Preview tokens ───────────────────────────────────────────────────────────

def test_admin_can_issue_preview_token(client, app):
    _login_admin(client, app)
    r = client.post('/api/cms/page/home/preview-token', json={'ttl_days': 7})
    assert r.status_code == 201
    body = r.get_json()
    assert 'token' in body and len(body['token']) > 20
    assert body['page_slug'] == 'home'


def test_preview_token_grants_draft_read(client, app):
    """A valid preview token lets an unauthenticated client read the draft."""
    _login_admin(client, app)
    client.patch('/api/cms/page/home/draft', json={
        'patches': [{'op': 'add', 'type': 'hero'}]
    })
    tok = client.post('/api/cms/page/home/preview-token').get_json()['token']
    # Use a fresh client (no inherited session cookies / auth state)
    fresh = app.test_client()
    r = fresh.get(f'/api/cms/page/home?state=draft&token={tok}')
    assert r.status_code == 200
    assert len(r.get_json()['template']['order']) == 1


def test_anonymous_without_token_cannot_read_draft(client, app):
    """No admin auth, no token → 401 on draft reads."""
    fresh = app.test_client()
    r = fresh.get('/api/cms/page/home?state=draft')
    assert r.status_code == 401


def test_expired_preview_token_rejected(client, app):
    _login_admin(client, app)
    # Manually insert an expired token
    with app.app_context():
        admin = User.query.filter_by(role='admin').first()
        tok = PreviewToken.issue('home', created_by=admin.id, ttl_days=1)
        tok.expires_at = datetime.utcnow() - timedelta(days=1)
        db.session.add(tok)
        db.session.commit()
        token_str = tok.token
    with client.session_transaction() as sess:
        sess.clear()
    r = client.get(f'/api/cms/page/home?state=draft&token={token_str}')
    assert r.status_code == 401


# ── Auth on writes ───────────────────────────────────────────────────────────

def test_anonymous_cannot_patch_draft(client):
    r = client.patch('/api/cms/page/home/draft', json={
        'patches': [{'op': 'add', 'type': 'hero'}]
    })
    assert r.status_code in (401, 403)


def test_anonymous_cannot_publish(client):
    r = client.post('/api/cms/page/home/publish')
    assert r.status_code in (401, 403)
