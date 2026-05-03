# app/routes/cms_ai.py
# Responsibility: AI-assisted CMS — given a prompt + the current page state +
# the available section schemas, ask Claude to emit a valid section instance
# the editor can drop into the page.

import json
import os

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user

from app.utils.errors import error_response
from app.utils.auth_decorators import requires_role


cms_ai_bp = Blueprint('cms_ai', __name__)


def _claude_client():
    """Return an Anthropic client, or None if no key configured."""
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        return None
    try:
        from anthropic import Anthropic
        return Anthropic(api_key=api_key)
    except Exception:
        return None


def _build_prompt(prompt, registry_types, page_context):
    """Construct the system + user prompt for section generation."""
    system = (
        "You are a layout assistant for a small nonprofit's website CMS. "
        "Given the user's intent and the available section types (with their "
        "JSON schemas), respond with a SINGLE JSON object describing one "
        "section to add. The JSON must be valid and contain exactly: "
        '{"type": "<one of the available types>", "settings": {...}, '
        '"blocks": [{"type": "...", "settings": {...}}, ...]}. '
        "Only include `blocks` if the section type has blocks. Use the field "
        "ids from the schema. Keep copy concise, friendly, and appropriate "
        "for a community emergency-preparedness organization. Do not include "
        "Markdown fences. Do not include any prose outside the JSON."
    )
    schemas_block = json.dumps(registry_types, indent=2)
    context_block = json.dumps(page_context or {}, indent=2)
    user = (
        f"AVAILABLE SECTION TYPES:\n{schemas_block}\n\n"
        f"CURRENT PAGE STATE (read-only context, do not duplicate):\n{context_block}\n\n"
        f"USER REQUEST:\n{prompt}\n\n"
        "Respond with one JSON object only."
    )
    return system, user


def _parse_response(text):
    """Parse Claude's response. Strips fences, finds first {...} object."""
    text = (text or '').strip()
    # Strip code fences if model added them
    if text.startswith('```'):
        text = text.split('```', 2)
        # text now might be ['', 'json\n{...}\n', ''] etc.
        text = text[1] if len(text) > 1 else ''
        # Remove leading "json\n" if present
        if text.startswith('json\n'):
            text = text[5:]
        if text.endswith('```'):
            text = text[:-3]
    text = text.strip()
    # Try direct parse first
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        pass
    # Fall back: find the first balanced {...}
    start = text.find('{')
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except (ValueError, TypeError):
                    return None
    return None


@cms_ai_bp.route('/cms/ai/section', methods=['POST'])
@requires_role('admin')
def generate_section():
    """Body: { prompt: str, page_slug?: str, page_context?: object }
       Returns: { type: str, settings: {...}, blocks?: [...] }
    """
    body = request.get_json(silent=True) or {}
    prompt = (body.get('prompt') or '').strip()
    if not prompt:
        return error_response('VALIDATION_FAILED', 400, {'detail': 'prompt is required'})

    reg = current_app.config.get('CMS_REGISTRY')
    if not reg:
        return error_response('SERVER_ERROR', 500, {'detail': 'cms registry not initialized'})
    types = reg.list_types()  # public schemas

    client = _claude_client()
    if not client:
        return error_response('SERVER_ERROR', 503, {'detail': 'ANTHROPIC_API_KEY not configured'})

    system, user = _build_prompt(prompt, types, body.get('page_context'))

    try:
        msg = client.messages.create(
            model=os.environ.get('CMS_AI_MODEL', 'claude-3-5-haiku-latest'),
            max_tokens=2000,
            system=system,
            messages=[{'role': 'user', 'content': user}],
        )
        # Concatenate all text blocks in the response
        text = ''.join(
            (b.text if hasattr(b, 'text') else '') for b in (msg.content or [])
        )
    except Exception as exc:                      # noqa: BLE001
        return error_response('SERVER_ERROR', 502, {'detail': f'AI request failed: {exc}'})

    section = _parse_response(text)
    if not isinstance(section, dict) or 'type' not in section:
        return error_response('SERVER_ERROR', 502, {
            'detail': 'AI response did not contain a valid section JSON',
            'raw': text[:1000],
        })

    # Validate against registry: type must exist; unknown setting keys dropped.
    type_id = section.get('type')
    type_entry = reg.get(type_id)
    if not type_entry:
        return error_response('SERVER_ERROR', 502, {
            'detail': f'AI selected unknown type {type_id!r}',
            'raw': text[:1000],
        })
    schema = type_entry['schema']
    valid_keys = {f['id'] for f in (schema.get('settings') or [])}
    settings = {k: v for k, v in (section.get('settings') or {}).items() if k in valid_keys}

    # Same for blocks
    valid_block_types = {b['type']: {f['id'] for f in (b.get('settings') or [])}
                         for b in (schema.get('blocks') or [])}
    out_blocks = []
    for b in (section.get('blocks') or []):
        bt = b.get('type')
        if bt not in valid_block_types:
            continue
        valid_block_keys = valid_block_types[bt]
        out_blocks.append({
            'type': bt,
            'settings': {k: v for k, v in (b.get('settings') or {}).items() if k in valid_block_keys},
        })

    result = {'type': type_id, 'settings': settings}
    if out_blocks:
        result['blocks'] = out_blocks
    return jsonify(result), 200
