# app/routes/page_sections.py
# Responsibility: Page section CRUD API — public read, admin write.

import json
from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_login import current_user

from app import db
from app.models.page_section import PageSection
from app.utils.errors import error_response
from app.utils.auth_decorators import requires_role

page_sections_bp = Blueprint('page_sections', __name__)

ALLOWED_BLOCK_TYPES = {
    'text_block', 'image_text', 'hero', 'cta_banner',
    'gallery', 'alert_box', 'two_column', 'spacer',
}


@page_sections_bp.route('/sections/<string:page_slug>', methods=['GET'])
def get_sections(page_slug):
    """Return all visible sections for a page, ordered. Public access."""
    sections = (
        PageSection.query
        .filter_by(page_slug=page_slug, visible=True)
        .order_by(PageSection.display_order)
        .all()
    )
    return jsonify({'sections': [s.to_dict() for s in sections]}), 200


@page_sections_bp.route('/sections/<string:page_slug>/all', methods=['GET'])
@requires_role('admin')
def get_all_sections(page_slug):
    """Return ALL sections for a page (including hidden) for admin view."""
    sections = (
        PageSection.query
        .filter_by(page_slug=page_slug)
        .order_by(PageSection.display_order)
        .all()
    )
    return jsonify({'sections': [s.to_dict() for s in sections]}), 200


@page_sections_bp.route('/sections/<string:page_slug>', methods=['POST'])
@requires_role('admin')
def create_section(page_slug):
    """Create a new section on a page. Admin only."""
    data = request.get_json(silent=True) or {}

    block_type = data.get('block_type', 'text_block')
    if block_type not in ALLOWED_BLOCK_TYPES:
        return error_response('VALIDATION_FAILED', 400, {'detail': f'block_type must be one of {sorted(ALLOWED_BLOCK_TYPES)}'})

    # Append at the end by default
    max_order = db.session.query(db.func.max(PageSection.display_order)).filter_by(page_slug=page_slug).scalar() or 0

    section = PageSection(
        page_slug=page_slug,
        block_type=block_type,
        title=data.get('title') or None,
        display_order=max_order + 1,
        visible=data.get('visible', True),
        updated_by=current_user.id,
    )
    section.set_content(data.get('content') or {})
    db.session.add(section)
    db.session.commit()
    return jsonify({'message': 'Section created.', 'section': section.to_dict()}), 201


@page_sections_bp.route('/sections/item/<int:section_id>', methods=['PATCH'])
@requires_role('admin')
def update_section(section_id):
    """Update a section's content, title, visibility, or order. Admin only."""
    section = PageSection.query.get(section_id)
    if not section:
        return error_response('NOT_FOUND', 404)

    data = request.get_json(silent=True) or {}

    if 'title' in data:
        section.title = data['title'] or None
    if 'content' in data:
        section.set_content(data['content'])
    if 'visible' in data:
        section.visible = bool(data['visible'])
    if 'display_order' in data:
        section.display_order = int(data['display_order'])
    if 'block_type' in data:
        bt = data['block_type']
        if bt not in ALLOWED_BLOCK_TYPES:
            return error_response('VALIDATION_FAILED', 400, {'detail': 'invalid block_type'})
        section.block_type = bt

    section.updated_at = datetime.utcnow()
    section.updated_by = current_user.id
    db.session.commit()
    return jsonify({'message': 'Section updated.', 'section': section.to_dict()}), 200


@page_sections_bp.route('/sections/item/<int:section_id>', methods=['DELETE'])
@requires_role('admin')
def delete_section(section_id):
    """Delete a section. Admin only."""
    section = PageSection.query.get(section_id)
    if not section:
        return error_response('NOT_FOUND', 404)
    db.session.delete(section)
    db.session.commit()
    return jsonify({'message': 'Section deleted.'}), 200


@page_sections_bp.route('/sections/reorder', methods=['POST'])
@requires_role('admin')
def reorder_sections():
    """Bulk-update display_order. Body: { sections: [{id, order}] }"""
    data = request.get_json(silent=True) or {}
    items = data.get('sections') or []
    if not isinstance(items, list):
        return error_response('VALIDATION_FAILED', 400, {'detail': 'sections must be an array'})

    updated = 0
    for item in items:
        sec = PageSection.query.get(item.get('id'))
        if sec:
            sec.display_order = int(item.get('order', sec.display_order))
            updated += 1

    db.session.commit()
    return jsonify({'message': f'Reordered {updated} sections.'}), 200
