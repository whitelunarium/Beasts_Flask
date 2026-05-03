# app/routes/cms_manifest.py
# Responsibility: Per-page editable-field schema for the live theme editor.
# Read-only, public access. The manifest is a constant — not stored in the DB.

from flask import Blueprint, jsonify

from app.utils.errors import error_response

cms_manifest_bp = Blueprint('cms_manifest', __name__)


# ─── Manifests ────────────────────────────────────────────────────────────────
# Each manifest declares the editable fields for one page.
# `kind` is 'site_config' (PATCH /api/site-config/<key>) or 'override'
# (POST /api/overrides/<slug>). `type` drives the editor widget.
# `preview_path` is the iframe src (with `?preview=1` appended by the editor).

MANIFESTS = {
    'home': {
        'page_slug':    'home',
        'page_title':   'Homepage',
        'preview_path': '/',
        'sections': [
            {
                'label': 'Hero',
                'fields': [
                    {'key': 'hero_headline',         'kind': 'site_config', 'type': 'text',  'label': 'Headline'},
                    {'key': 'hero_subline',          'kind': 'site_config', 'type': 'text',  'label': 'Sub-headline'},
                    {'key': 'homepage_banner_image', 'kind': 'site_config', 'type': 'image', 'label': 'Hero image'},
                ],
            },
            {
                'label': 'About blurb',
                'fields': [
                    {'key': 'about_blurb', 'kind': 'site_config', 'type': 'richtext', 'label': 'About paragraph'},
                ],
            },
            {
                'label': 'Footer',
                'fields': [
                    {'key': 'footer_tagline',   'kind': 'site_config', 'type': 'text', 'label': 'Footer tagline'},
                    {'key': 'footer_copyright', 'kind': 'site_config', 'type': 'text', 'label': 'Footer copyright'},
                ],
            },
        ],
    },
    'about': {
        'page_slug':    'about',
        'page_title':   'About',
        'preview_path': '/pages/about.html',
        'sections': [
            {
                'label': 'Header',
                'fields': [
                    {'key': 'about_banner_image', 'kind': 'site_config', 'type': 'image', 'label': 'About banner image'},
                ],
            },
            {
                'label': 'Who We Are',
                'fields': [
                    {'key': 'about_who_para1', 'kind': 'site_config', 'type': 'richtext', 'label': 'Paragraph 1'},
                    {'key': 'about_who_para2', 'kind': 'site_config', 'type': 'richtext', 'label': 'Paragraph 2'},
                ],
            },
            {
                'label': 'History',
                'fields': [
                    {'key': 'about_history', 'kind': 'site_config', 'type': 'richtext', 'label': 'History section'},
                ],
            },
            {
                'label': 'Mission',
                'fields': [
                    {'key': 'about_mission', 'kind': 'site_config', 'type': 'richtext', 'label': 'Mission statement'},
                ],
            },
        ],
    },
    'programs': {
        'page_slug':    'programs',
        'page_title':   'Programs and Services',
        'preview_path': '/pages/programs-and-services.html',
        'sections': [
            {
                'label': 'Header',
                'fields': [
                    {'key': 'programs_banner_image', 'kind': 'site_config', 'type': 'image', 'label': 'Programs banner image'},
                ],
            },
            {
                'label': 'PNEC',
                'fields': [
                    {'key': 'programs_pnec_para', 'kind': 'site_config', 'type': 'richtext', 'label': 'PNEC programs paragraph'},
                ],
            },
            {
                'label': 'Fire Safe Council',
                'fields': [
                    {'key': 'programs_fsc_para', 'kind': 'site_config', 'type': 'richtext', 'label': 'FSC paragraph'},
                ],
            },
            {
                'label': 'PACT',
                'fields': [
                    {'key': 'programs_pact_para', 'kind': 'site_config', 'type': 'richtext', 'label': 'PACT paragraph'},
                ],
            },
            {
                'label': 'Large Animals',
                'fields': [
                    {'key': 'programs_large_animal_para', 'kind': 'site_config', 'type': 'richtext', 'label': 'Large animal paragraph'},
                ],
            },
        ],
    },
}


@cms_manifest_bp.route('/cms/manifest/<string:page_slug>', methods=['GET'])
def get_manifest(page_slug):
    """Return the editable-field manifest for a page. Public — no auth."""
    manifest = MANIFESTS.get(page_slug)
    if not manifest:
        return error_response('NOT_FOUND', 404)
    return jsonify(manifest), 200
