# app/routes/admin_publish.py
# v3.15 — admin endpoints for the Live Theme Editor:
#   - POST /api/admin/publish/file        commit a single file change to GitHub
#   - POST /api/admin/publish/files       commit a batch of file changes (atomic)
#   - GET  /api/admin/publish/status      latest workflow run status
#   - GET  /api/admin/publish/file        GET current content of a file from GitHub
#   - POST /api/admin/ai/section          generate page section HTML via Groq

import os
from flask import Blueprint, jsonify, request, current_app

from app.services import github_publish_service as gh
from app.utils.errors import error_response

admin_publish_bp = Blueprint('admin_publish', __name__)


# ─── Auth ─────────────────────────────────────────────────────────

def _require_admin():
    """Same gate as the volunteer dashboard: session role==admin, OR
    X-PNEC-Admin-Key header matches ADMIN_PASSWORD."""
    from flask import session
    role = session.get('role') or session.get('user_role')
    if role == 'admin':
        return True
    key = request.headers.get('X-PNEC-Admin-Key')
    if key and key == current_app.config.get('ADMIN_PASSWORD'):
        return True
    return False


# ─── GitHub publish ───────────────────────────────────────────────

@admin_publish_bp.route('/admin/publish/file', methods=['GET'])
def get_file():
    if not _require_admin():
        return error_response('UNAUTHORIZED', 401)
    path = (request.args.get('path') or '').strip()
    if not path or '..' in path or path.startswith('/'):
        return error_response('INVALID_PATH', 400)
    try:
        content, sha = gh.get_file(path)
        if content is None:
            return error_response('NOT_FOUND', 404, {'detail': f'{path} not in repo'})
        return jsonify({'ok': True, 'path': path, 'content': content, 'sha': sha}), 200
    except gh.GitHubPublishError as e:
        return error_response('GITHUB_ERROR', 502, {'detail': str(e), 'status': e.status})


@admin_publish_bp.route('/admin/publish/file', methods=['POST'])
def publish_one_file():
    if not _require_admin():
        return error_response('UNAUTHORIZED', 401)

    data = request.get_json(silent=True) or {}
    path = (data.get('path') or '').strip()
    content = data.get('content')
    message = (data.get('message') or '').strip() or 'Edit via PNEC Live Theme Editor'

    if not path or '..' in path or path.startswith('/'):
        return error_response('INVALID_PATH', 400)
    if not isinstance(content, str):
        return error_response('INVALID_CONTENT', 400)
    if len(content) > 5_000_000:
        return error_response('CONTENT_TOO_LARGE', 400, {'detail': 'Max 5 MB per file.'})

    try:
        result = gh.commit_single_file(
            path=path, new_content=content,
            message=message,
            committer_name='PNEC Live Editor',
            committer_email='editor@powaynec.com',
        )
        try:
            current_app.logger.info(
                f'admin.publish.file ok path={path} sha={result.get("commit_sha")}'
            )
        except Exception:
            pass
        return jsonify({'ok': True, **result}), 200
    except gh.GitHubPublishError as e:
        return error_response('GITHUB_ERROR', 502, {'detail': str(e), 'status': e.status})


@admin_publish_bp.route('/admin/publish/files', methods=['POST'])
def publish_many_files():
    if not _require_admin():
        return error_response('UNAUTHORIZED', 401)

    data = request.get_json(silent=True) or {}
    files = data.get('files') or []
    message = (data.get('message') or '').strip() or 'Batch edit via PNEC Live Theme Editor'

    if not isinstance(files, list) or not files:
        return error_response('NO_FILES', 400, {'detail': 'Provide files: [{path, content}, ...]'})
    if len(files) > 30:
        return error_response('TOO_MANY_FILES', 400, {'detail': 'Max 30 files per commit.'})

    cleaned = []
    for f in files:
        if not isinstance(f, dict):
            return error_response('INVALID_FILE_ENTRY', 400)
        path = (f.get('path') or '').strip()
        content = f.get('content')
        if not path or '..' in path or path.startswith('/'):
            return error_response('INVALID_PATH', 400, {'detail': f'Bad path: {path}'})
        if not isinstance(content, str):
            return error_response('INVALID_CONTENT', 400, {'detail': f'Bad content for {path}'})
        if len(content) > 5_000_000:
            return error_response('CONTENT_TOO_LARGE', 400, {'detail': f'{path} > 5 MB'})
        cleaned.append({'path': path, 'content': content})

    try:
        result = gh.commit_multiple_files(
            files=cleaned, message=message,
            committer_name='PNEC Live Editor',
            committer_email='editor@powaynec.com',
        )
        try:
            current_app.logger.info(
                f'admin.publish.files ok count={result.get("count")} sha={result.get("commit_sha")}'
            )
        except Exception:
            pass
        return jsonify({'ok': True, **result}), 200
    except gh.GitHubPublishError as e:
        return error_response('GITHUB_ERROR', 502, {'detail': str(e), 'status': e.status})


@admin_publish_bp.route('/admin/publish/status', methods=['GET'])
def workflow_status():
    if not _require_admin():
        return error_response('UNAUTHORIZED', 401)
    runs = gh.workflow_runs(per_page=int(request.args.get('per_page', 5)))
    items = []
    for r in runs:
        items.append({
            'id':           r.get('id'),
            'name':         r.get('name'),
            'status':       r.get('status'),        # queued/in_progress/completed
            'conclusion':   r.get('conclusion'),    # success/failure/cancelled/null
            'head_commit':  (r.get('head_commit') or {}).get('message'),
            'head_sha':     (r.get('head_commit') or {}).get('id'),
            'html_url':     r.get('html_url'),
            'created_at':   r.get('created_at'),
            'updated_at':   r.get('updated_at'),
        })
    return jsonify({'ok': True, 'items': items}), 200


# ─── Groq AI section generation ───────────────────────────────────

import requests as _requests


@admin_publish_bp.route('/admin/ai/section', methods=['POST'])
def ai_section():
    """Generate page-section HTML via Groq.

    Body: {
      prompt:        "Plain-English description of what the section should say"
      section_kind:  "hero" | "card_list" | "image_with_text" | "cta" | "faq" | "text"
      tone:          "neighborly" (default) | "urgent" | "formal"
      page_context:  optional short note about the page the section will live on
    }

    Returns: { html, model, usage }
    """
    if not _require_admin():
        return error_response('UNAUTHORIZED', 401)

    data = request.get_json(silent=True) or {}
    user_prompt   = (data.get('prompt') or '').strip()
    section_kind  = (data.get('section_kind') or 'text').strip()
    tone          = (data.get('tone') or 'neighborly').strip()
    page_context  = (data.get('page_context') or '').strip()

    if not user_prompt or len(user_prompt) > 4000:
        return error_response('INVALID_PROMPT', 400)

    api_key = current_app.config.get('GROQ_API_KEY') or os.environ.get('GROQ_API_KEY')
    if not api_key:
        return error_response('GROQ_NOT_CONFIGURED', 503,
                              {'detail': 'GROQ_API_KEY env var is required.'})

    model = current_app.config.get('GROQ_MODEL') or 'llama-3.3-70b-versatile'
    url = (current_app.config.get('GROQ_API_URL') or 'https://api.groq.com/openai/v1').rstrip('/') + '/chat/completions'

    system = (
        "You write semantic HTML section blocks for the Poway Neighborhood "
        "Emergency Corps (PNEC) website. Output ONLY the HTML — no markdown "
        "fences, no preamble, no closing remarks. Use existing brand classes "
        "where helpful (cream + forest theme). Heading levels start at h2. "
        "Tone: " + tone + ". Section kind: " + section_kind + ". "
        + (("Page context: " + page_context + ". ") if page_context else "")
        + "Never invent statistics, addresses, or volunteer names. Real "
        "phone numbers PNEC publishes: powaynec@gmail.com (general), "
        "858-668-1250 (homebound helpline), 2-1-1 (financial aid). "
        "Real upcoming event: 12th Annual Emergency & Safety Fair, "
        "May 23 2026, Old Poway Park, 9 AM-1 PM. Keep responses concise "
        "and actionable — Poway residents are reading these to make decisions."
    )

    try:
        resp = _requests.post(url, timeout=30, headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }, json={
            'model': model,
            'temperature': 0.5,
            'max_tokens': 1200,
            'messages': [
                {'role': 'system', 'content': system},
                {'role': 'user',   'content': user_prompt},
            ],
        })
        if not resp.ok:
            return error_response('GROQ_API_ERROR', 502, {
                'detail': f'Groq returned {resp.status_code}',
                'body': resp.text[:400],
            })
        body = resp.json()
        html = ((body.get('choices') or [{}])[0].get('message') or {}).get('content') or ''
        # Strip any accidental markdown fences
        html = html.strip()
        if html.startswith('```'):
            html = html.split('\n', 1)[-1] if '\n' in html else ''
            if html.endswith('```'):
                html = html[:-3].rstrip()
        return jsonify({
            'ok': True,
            'html': html,
            'model': body.get('model') or model,
            'usage': body.get('usage') or {},
        }), 200
    except Exception as e:
        try:
            current_app.logger.exception('admin.ai_section failed')
        except Exception:
            pass
        return error_response('AI_ERROR', 502, {'detail': str(e)[:200]})
