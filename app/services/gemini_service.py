# app/services/gemini_service.py
# Responsibility: Server-side Gemini proxy for website assistant features.

import requests
from flask import current_app


def generate_chat_response(system_prompt, user_message, history=None):
    """Return generated text from Gemini, or a typed error key."""
    api_key = current_app.config.get('GEMINI_API_KEY')
    if not api_key:
        return None, 'GEMINI_NOT_CONFIGURED'

    system_prompt = (system_prompt or '').strip()
    user_message = (user_message or '').strip()
    if not user_message:
        return None, 'MISSING_MESSAGE'

    model = current_app.config.get('GEMINI_MODEL', 'gemini-2.5-flash')
    api_base = current_app.config.get('GEMINI_API_URL', 'https://generativelanguage.googleapis.com/v1beta').rstrip('/')
    endpoint = f'{api_base}/models/{model}:generateContent'

    payload = {
        'systemInstruction': {
            'parts': [{'text': system_prompt}]
        },
        'contents': _build_contents(history, user_message),
        'generationConfig': {
            'temperature': 0.5,
            'topP': 0.9,
            'maxOutputTokens': 1200,
        },
    }

    try:
        response = requests.post(
            endpoint,
            params={'key': api_key},
            json=payload,
            timeout=20,
        )
    except requests.RequestException as exc:
        current_app.logger.warning('Gemini proxy network error: %s', exc)
        return None, {
            'code': 'GEMINI_NETWORK_ERROR',
            'detail': 'Gemini request could not reach Google. Check internet access, DNS, and firewall settings.',
        }

    if response.status_code >= 400:
        detail = _extract_gemini_error(response)
        current_app.logger.warning('Gemini API error %s: %s', response.status_code, detail)
        return None, {
            'code': 'GEMINI_API_ERROR',
            'detail': f'Gemini API returned {response.status_code}: {detail}',
        }

    try:
        data = response.json()
    except ValueError:
        current_app.logger.warning('Gemini returned a non-JSON response.')
        return None, {
            'code': 'GEMINI_BAD_RESPONSE',
            'detail': 'Gemini returned a response the server could not parse.',
        }

    text = _extract_gemini_text(data)
    if not text:
        current_app.logger.warning('Gemini response did not include answer text: %s', data)
        return None, {
            'code': 'GEMINI_EMPTY_RESPONSE',
            'detail': 'Gemini returned no answer text.',
        }

    return text, None


def _extract_gemini_text(data):
    candidates = data.get('candidates') if isinstance(data, dict) else None
    if not candidates:
        return ''

    parts = candidates[0].get('content', {}).get('parts', [])
    return ''.join(part.get('text', '') for part in parts if isinstance(part, dict)).strip()


def _extract_gemini_error(response):
    try:
        data = response.json()
    except ValueError:
        return response.text[:300] or 'No error details returned.'

    if not isinstance(data, dict):
        return 'Unexpected error response.'

    error = data.get('error')
    if isinstance(error, dict):
        return error.get('message') or error.get('status') or 'No error details returned.'

    return data.get('message') or data.get('detail') or 'No error details returned.'


def _build_contents(history, user_message):
    contents = []
    for turn in (history or [])[-8:]:
        if not isinstance(turn, dict):
            continue
        role = turn.get('role')
        content = str(turn.get('content') or '').strip()
        if not content:
            continue
        contents.append({
            'role': 'model' if role == 'assistant' else 'user',
            'parts': [{'text': content[:2000]}],
        })

    contents.append({
        'role': 'user',
        'parts': [{'text': user_message}],
    })
    return contents
