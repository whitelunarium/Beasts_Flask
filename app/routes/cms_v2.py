# app/routes/cms_v2.py
# Responsibility: v2 CMS API — page-level section/block composition with
# draft/publish workflow. Public read of the published state, admin (or
# preview-token) read of the draft, admin-only writes.
#
# Endpoints (all under /api):
#   GET    /cms/sections-registry          List available section types + schemas
#   GET    /cms/page/<slug>                Read a page (state=published default)
#   GET    /cms/page/<slug>/draft          Convenience for draft-state read
#   PATCH  /cms/page/<slug>/draft          Apply a list of patches to the draft
#   POST   /cms/page/<slug>/publish        Copy draft → published
#   GET    /cms/render                     Render a single section to HTML
#   POST   /cms/page/<slug>/preview-token  Issue a 7-day share-preview token

import secrets
from datetime import datetime
from copy import deepcopy

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user

from app import db
from app.models.page_template import PageTemplate, STATE_DRAFT, STATE_PUBLISHED, VALID_STATES
from app.models.preview_token import PreviewToken
from app.services.cms_renderer import render_page, render_section
from app.utils.errors import error_response
from app.utils.auth_decorators import requires_role


cms_v2_bp = Blueprint('cms_v2', __name__)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _registry():
    """Pull the registry instance off the Flask app."""
    return current_app.config.get('CMS_REGISTRY')


def _get_or_create_template(page_slug, state):
    """Return the PageTemplate row for this (slug, state). Creates an empty
    draft on demand. Published rows are NOT auto-created (caller publishes)."""
    row = PageTemplate.query.filter_by(page_slug=page_slug, state=state).first()
    if row:
        return row
    if state == STATE_DRAFT:
        row = PageTemplate(
            page_slug=page_slug,
            state=STATE_DRAFT,
            template_json='{"sections":{},"order":[]}',
        )
        db.session.add(row)
        db.session.commit()
        return row
    return None


def _sid():
    """Generate a stable section/block id (URL-safe, 12 chars)."""
    return secrets.token_urlsafe(8)[:12].replace('-', 'a').replace('_', 'b')


def _is_admin():
    return (current_user.is_authenticated
            and getattr(current_user, 'role', None) == 'admin')


def _check_token(page_slug, token):
    """Return True if token grants read access to this page's draft."""
    if not token:
        return False
    row = PreviewToken.query.filter_by(token=token).first()
    return bool(row and row.is_valid_for(page_slug))


# ─── Sections registry endpoint ──────────────────────────────────────────────

@cms_v2_bp.route('/cms/sections-registry', methods=['GET'])
def get_sections_registry():
    """Return the list of section types available to instantiate.
    Public: the editor needs this to render its picker, and hydrate.js may
    use it to pre-validate. No template source is exposed here."""
    reg = _registry()
    if not reg:
        return error_response('SERVER_ERROR', 500, {'detail': 'cms registry not initialized'})
    return jsonify({'sections': reg.list_types()}), 200


# ─── Page read endpoints ─────────────────────────────────────────────────────

@cms_v2_bp.route('/cms/page/<string:page_slug>', methods=['GET'])
def get_page(page_slug):
    """Read a page's template + rendered sections.

    Query params:
      state:  'published' (default) or 'draft'
      token:  preview token (only relevant when state=draft)
    """
    state = (request.args.get('state') or STATE_PUBLISHED).strip()
    if state not in VALID_STATES:
        return error_response('VALIDATION_FAILED', 400, {'detail': 'invalid state'})

    if state == STATE_DRAFT:
        token = request.args.get('token')
        if not (_is_admin() or _check_token(page_slug, token)):
            return error_response('UNAUTHORIZED', 401)

    row = PageTemplate.query.filter_by(page_slug=page_slug, state=state).first()
    if not row:
        # Returning empty template is friendlier for the FE than 404 — the page
        # simply has no v2 sections yet, which is the expected state for new pages.
        return jsonify({
            'page_slug':     page_slug,
            'state':         state,
            'template':      {'sections': {}, 'order': []},
            'sections_html': {},
            'updated_at':    None,
        }), 200

    template = row.get_template()
    reg = _registry()
    sections_html = render_page(template, reg) if reg else {}
    return jsonify({
        'page_slug':     row.page_slug,
        'state':         row.state,
        'template':      template,
        'sections_html': sections_html,
        'updated_at':    row.updated_at.isoformat() if row.updated_at else None,
        'published_at':  row.published_at.isoformat() if row.published_at else None,
    }), 200


@cms_v2_bp.route('/cms/page/<string:page_slug>/draft', methods=['GET'])
@requires_role('admin')
def get_page_draft(page_slug):
    """Admin convenience: same as GET /cms/page/<slug>?state=draft."""
    request.args = request.args.copy()
    # delegate
    return get_page(page_slug)


# ─── Page write endpoint ─────────────────────────────────────────────────────

@cms_v2_bp.route('/cms/page/<string:page_slug>/draft', methods=['PATCH'])
@requires_role('admin')
def patch_page_draft(page_slug):
    """Apply a list of patches to the draft template.

    Body: { "patches": [ { "op": ..., ... }, ... ] }

    Supported ops:
      add       {op:'add',    sid?, type, settings?, index?}
      remove    {op:'remove', sid}
      duplicate {op:'duplicate', sid, new_sid?}
      reorder   {op:'reorder', order: [sid, sid, ...]}
      set       {op:'set',    sid, key, value}            update one setting
      bulk      {op:'bulk_set', sid, settings: {...}}     replace section settings
      visibility{op:'visibility', sid, visible: bool}
      add_block {op:'add_block', sid, block_type, settings?}
      remove_block {op:'remove_block', sid, bid}
      reorder_blocks {op:'reorder_blocks', sid, block_order: [bid, ...]}
      set_block {op:'set_block', sid, bid, key, value}

    Returns the updated template plus the rendered HTML for any sections that
    changed (so the editor can hot-swap exactly those).
    """
    data = request.get_json(silent=True) or {}
    patches = data.get('patches')
    if not isinstance(patches, list):
        return error_response('VALIDATION_FAILED', 400, {'detail': 'patches must be a list'})

    row = _get_or_create_template(page_slug, STATE_DRAFT)
    template = row.get_template()
    reg = _registry()
    if not reg:
        return error_response('SERVER_ERROR', 500, {'detail': 'cms registry not initialized'})

    affected = set()  # sids whose rendered output should be returned

    for patch in patches:
        op = (patch or {}).get('op')
        if op == 'add':
            type_id = patch.get('type')
            if not type_id or not reg.get(type_id):
                return error_response('VALIDATION_FAILED', 400,
                                      {'detail': f'unknown section type {type_id!r}'})
            sid = patch.get('sid') or _sid()
            settings = patch.get('settings') or reg.default_settings(type_id)
            template['sections'][sid] = {
                'type':        type_id,
                'settings':    settings,
                'visible':     True,
                'blocks':      {},
                'block_order': [],
            }
            index = patch.get('index')
            if isinstance(index, int) and 0 <= index <= len(template['order']):
                template['order'].insert(index, sid)
            else:
                template['order'].append(sid)
            affected.add(sid)

        elif op == 'remove':
            sid = patch.get('sid')
            template['sections'].pop(sid, None)
            template['order'] = [x for x in template['order'] if x != sid]

        elif op == 'duplicate':
            sid = patch.get('sid')
            src = template['sections'].get(sid)
            if not src:
                continue
            new_sid = patch.get('new_sid') or _sid()
            template['sections'][new_sid] = deepcopy(src)
            # Insert the duplicate immediately after the source in `order`
            try:
                idx = template['order'].index(sid)
                template['order'].insert(idx + 1, new_sid)
            except ValueError:
                template['order'].append(new_sid)
            affected.add(new_sid)

        elif op == 'reorder':
            new_order = patch.get('order')
            if not isinstance(new_order, list):
                return error_response('VALIDATION_FAILED', 400, {'detail': 'order must be a list'})
            # Only allow reordering of existing sids; drop unknowns silently
            known = set(template['sections'].keys())
            template['order'] = [x for x in new_order if x in known]

        elif op == 'set':
            sid = patch.get('sid')
            key = patch.get('key')
            section = template['sections'].get(sid)
            if section is None or not key:
                continue
            section.setdefault('settings', {})
            section['settings'][key] = patch.get('value')
            affected.add(sid)

        elif op == 'bulk_set':
            sid = patch.get('sid')
            section = template['sections'].get(sid)
            if section is None:
                continue
            section['settings'] = patch.get('settings') or {}
            affected.add(sid)

        elif op == 'visibility':
            sid = patch.get('sid')
            section = template['sections'].get(sid)
            if section is None:
                continue
            section['visible'] = bool(patch.get('visible', True))
            affected.add(sid)

        elif op == 'replace_template':
            # Wholesale replace the draft template (used by undo/redo).
            new_t = patch.get('template') or {}
            if not isinstance(new_t, dict):
                return error_response('VALIDATION_FAILED', 400, {'detail': 'template must be an object'})
            new_t.setdefault('sections', {})
            new_t.setdefault('order', [])
            template['sections'] = new_t['sections']
            template['order']    = new_t['order']
            affected.update(new_t['sections'].keys())

        elif op == 'device_visibility':
            sid = patch.get('sid')
            section = template['sections'].get(sid)
            if section is None:
                continue
            devices = patch.get('devices') or ['desktop', 'tablet', 'mobile']
            allowed = {'desktop', 'tablet', 'mobile'}
            section['device_visibility'] = [d for d in devices if d in allowed]
            affected.add(sid)

        elif op == 'add_block':
            sid = patch.get('sid')
            section = template['sections'].get(sid)
            if section is None:
                continue
            bid = patch.get('bid') or _sid()
            section.setdefault('blocks', {})
            section.setdefault('block_order', [])
            section['blocks'][bid] = {
                'type': patch.get('block_type') or 'item',
                'settings': patch.get('settings') or {},
            }
            section['block_order'].append(bid)
            affected.add(sid)

        elif op == 'remove_block':
            sid = patch.get('sid')
            bid = patch.get('bid')
            section = template['sections'].get(sid)
            if section is None:
                continue
            section.get('blocks', {}).pop(bid, None)
            section['block_order'] = [x for x in section.get('block_order', []) if x != bid]
            affected.add(sid)

        elif op == 'reorder_blocks':
            sid = patch.get('sid')
            section = template['sections'].get(sid)
            if section is None:
                continue
            new_order = patch.get('block_order') or []
            known = set(section.get('blocks', {}).keys())
            section['block_order'] = [x for x in new_order if x in known]
            affected.add(sid)

        elif op == 'set_block':
            sid = patch.get('sid')
            bid = patch.get('bid')
            key = patch.get('key')
            section = template['sections'].get(sid)
            if section is None or not key:
                continue
            block = section.get('blocks', {}).get(bid)
            if block is None:
                continue
            block.setdefault('settings', {})
            block['settings'][key] = patch.get('value')
            affected.add(sid)

        else:
            return error_response('VALIDATION_FAILED', 400, {'detail': f'unknown op {op!r}'})

    row.set_template(template)
    row.updated_at = datetime.utcnow()
    row.updated_by = current_user.id if current_user.is_authenticated else None
    db.session.commit()

    # Re-render only the sections that changed
    rendered = {}
    for sid in affected:
        if sid in template['sections']:
            rendered[sid] = render_section(sid, template['sections'][sid], reg)

    return jsonify({
        'template':       template,
        'sections_html':  rendered,
        'affected_sids':  sorted(affected),
    }), 200


# ─── Publish ─────────────────────────────────────────────────────────────────

@cms_v2_bp.route('/cms/page/<string:page_slug>/publish', methods=['POST'])
@requires_role('admin')
def publish_page(page_slug):
    """Copy draft → published. Idempotent — produces the same outcome whether
    a published row exists or not."""
    draft = PageTemplate.query.filter_by(page_slug=page_slug, state=STATE_DRAFT).first()
    if not draft:
        return error_response('NOT_FOUND', 404, {'detail': 'no draft to publish'})

    pub = PageTemplate.query.filter_by(page_slug=page_slug, state=STATE_PUBLISHED).first()
    now = datetime.utcnow()
    if pub:
        pub.template_json = draft.template_json
        pub.published_at  = now
        pub.published_by  = current_user.id
        pub.updated_at    = now
        pub.updated_by    = current_user.id
    else:
        pub = PageTemplate(
            page_slug=page_slug,
            state=STATE_PUBLISHED,
            template_json=draft.template_json,
            updated_by=current_user.id,
            published_at=now,
            published_by=current_user.id,
        )
        db.session.add(pub)
    db.session.commit()
    return jsonify({'message': 'Published.', 'page_slug': page_slug,
                    'published_at': now.isoformat()}), 200


# ─── Single-section render ───────────────────────────────────────────────────

@cms_v2_bp.route('/cms/render', methods=['GET'])
def render_one_section():
    """Render one section to HTML. Used by the editor to hot-swap sections in
    the iframe without a full reload, and by hydrate.js to live-preview edits.

    Query params: page=<slug>, section=<sid>, state=draft|published, token=...
    """
    page_slug = request.args.get('page')
    sid       = request.args.get('section')
    state     = (request.args.get('state') or STATE_PUBLISHED).strip()
    if not (page_slug and sid):
        return error_response('VALIDATION_FAILED', 400, {'detail': 'page and section required'})
    if state not in VALID_STATES:
        return error_response('VALIDATION_FAILED', 400, {'detail': 'invalid state'})
    if state == STATE_DRAFT:
        token = request.args.get('token')
        if not (_is_admin() or _check_token(page_slug, token)):
            return error_response('UNAUTHORIZED', 401)
    row = PageTemplate.query.filter_by(page_slug=page_slug, state=state).first()
    if not row:
        return error_response('NOT_FOUND', 404)
    template = row.get_template()
    section_data = (template.get('sections') or {}).get(sid)
    if not section_data:
        return error_response('NOT_FOUND', 404, {'detail': f'section {sid!r} not found'})
    reg = _registry()
    if not reg:
        return error_response('SERVER_ERROR', 500, {'detail': 'cms registry not initialized'})
    html = render_section(sid, section_data, reg)
    return jsonify({
        'section_id':   sid,
        'section_type': section_data.get('type'),
        'html':         html,
    }), 200


# ─── Preview tokens ──────────────────────────────────────────────────────────

@cms_v2_bp.route('/cms/page/<string:page_slug>/preview-token', methods=['POST'])
@requires_role('admin')
def issue_preview_token(page_slug):
    """Issue a 7-day token that grants read-only access to the page draft."""
    body = request.get_json(silent=True) or {}
    ttl_days = int(body.get('ttl_days') or 7)
    if ttl_days < 1 or ttl_days > 60:
        return error_response('VALIDATION_FAILED', 400, {'detail': 'ttl_days 1..60'})
    tok = PreviewToken.issue(page_slug, created_by=current_user.id, ttl_days=ttl_days)
    db.session.add(tok)
    db.session.commit()
    return jsonify({'token': tok.token, 'expires_at': tok.expires_at.isoformat(),
                    'page_slug': page_slug}), 201
