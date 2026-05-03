# app/services/cms_renderer.py
# Responsibility: Render a single CMS section to HTML using the Liquid template
# from the registry. Wraps output in a stable container with data attributes the
# editor uses to target the section (matches Shopify's `id="shopify-section-..."`
# convention).

from html import escape as html_escape

from liquid import Environment


# Module-level Liquid environment; safe to share across requests.
_env = Environment()


def render_section(section_id, section_data, registry):
    """Render one section dict to a wrapper HTML string.

    Args:
        section_id:    The unique sid (string) within the page's template.
        section_data:  {type, settings, visible, blocks, block_order}
        registry:      CmsRegistry instance used to look up the template.

    Returns:
        HTML string. On lookup or render failure, returns a sentinel comment so
        the editor can still detect the section in the DOM tree.
    """
    type_id = (section_data or {}).get('type')
    settings = (section_data or {}).get('settings') or {}
    visible = bool((section_data or {}).get('visible', True))
    blocks = (section_data or {}).get('blocks') or {}
    block_order = (section_data or {}).get('block_order') or []
    ordered_blocks = [
        {'id': bid, **(blocks.get(bid) or {})}
        for bid in block_order if bid in blocks
    ]

    entry = registry.get(type_id)
    if not entry:
        return _wrap(section_id, type_id or 'unknown', visible,
                     f'<!-- cms: unknown section type {html_escape(str(type_id))} -->')

    try:
        template = _env.from_string(entry['template_source'])
        body = template.render(
            section={'id': section_id, 'type': type_id, 'settings': settings,
                     'blocks': ordered_blocks},
            settings=settings,
            blocks=ordered_blocks,
        )
    except Exception as exc:                     # noqa: BLE001 — surface to dev console
        body = (f'<!-- cms: render error for {html_escape(type_id)}: '
                f'{html_escape(str(exc))} -->')

    if not visible:
        body = f'<!-- cms: section hidden -->{body}'

    return _wrap(section_id, type_id, visible, body)


def _wrap(section_id, type_id, visible, body):
    return (
        f'<div id="cms-section-{html_escape(str(section_id))}"'
        f' data-cms-section-id="{html_escape(str(section_id))}"'
        f' data-cms-section-type="{html_escape(str(type_id))}"'
        f' data-cms-section-visible="{ "true" if visible else "false" }">'
        f'{body}</div>'
    )


def render_page(template_dict, registry):
    """Render every section in the page template, in `order`.

    Returns a dict {section_id: html_string}. Sections in `sections` but missing
    from `order` are rendered too (defensive).
    """
    sections  = (template_dict or {}).get('sections') or {}
    order     = (template_dict or {}).get('order') or []
    out       = {}
    for sid in order:
        if sid in sections:
            out[sid] = render_section(sid, sections[sid], registry)
    # Render any orphan sections not in order (helps debug stale state)
    for sid, sdata in sections.items():
        if sid not in out:
            out[sid] = render_section(sid, sdata, registry)
    return out
