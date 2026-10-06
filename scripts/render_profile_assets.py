#!/usr/bin/env python3
"""Generate the profile's small, self-contained SVG cards and tool labels."""
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[1] / 'assets'
PALETTES = {
    'dark': dict(bg='#1c1816', end='#261d17', edge='#493427', ink='#f8f1e6',
                 muted='#b6a89a', amber='#faa544', sleeve='#36271e', disc='#201a17'),
    'light': dict(bg='#fcf8f1', end='#f2e8d9', edge='#decbb3', ink='#30241c',
                  muted='#796352', amber='#b9672e', sleeve='#eed6b5', disc='#f9efdf'),
}


def project_card(theme, compact=False):
    c = PALETTES[theme]
    width, height = (480, 166) if compact else (800, 186)
    art = 'translate(26 32) scale(.84)' if compact else 'translate(39 36)'
    typography = (
        f'<text x="150" y="79" font-size="34" font-weight="700" letter-spacing="-1.1">Meloark</text>'
        f'<text x="152" y="110" font-size="17" fill="{c["muted"]}">A home for your music.</text>'
        if compact else
        f'<text x="204" y="43" font-size="13" font-weight="600" letter-spacing="1.6" fill="{c["amber"]}">CURRENTLY BUILDING</text>'
        f'<text x="201" y="91" font-size="42" font-weight="700" letter-spacing="-1.3">Meloark</text>'
        f'<text x="204" y="122" font-size="19" fill="{c["muted"]}">A home for your music.</text>'
        f'<text x="204" y="153" font-size="13" fill="{c["muted"]}">Local files · Playlists · Synced lyrics</text>'
    )
    arrow_x, arrow_y = (443, 82) if compact else (750, 93)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">Meloark</title>
  <desc id="desc">A home for your music. A local-first player with playlists and synchronized lyrics.</desc>
  <defs>
    <linearGradient id="surface" x2="1" y2="1"><stop stop-color="{c['bg']}"/><stop offset="1" stop-color="{c['end']}"/></linearGradient>
    <linearGradient id="sleeve" x2="1" y2="1"><stop stop-color="{c['sleeve']}"/><stop offset="1" stop-color="{c['bg']}"/></linearGradient>
  </defs>
  <rect x=".5" y=".5" width="{width-1}" height="{height-1}" rx="16" fill="url(#surface)" stroke="{c['edge']}"/>
  <g transform="{art}">
    <rect x="19" y="-4" width="106" height="112" rx="8" transform="rotate(8 72 52)" fill="{c['sleeve']}" stroke="{c['edge']}"/>
    <rect x="7" y="1" width="106" height="112" rx="8" transform="rotate(-7 60 57)" fill="{c['bg']}" stroke="{c['edge']}"/>
    <rect width="106" height="112" rx="8" fill="url(#sleeve)" stroke="{c['amber']}" stroke-opacity=".5"/>
    <circle cx="53" cy="54" r="35" fill="{c['disc']}" stroke="{c['amber']}" stroke-opacity=".3"/>
    <circle cx="53" cy="54" r="28" fill="none" stroke="{c['amber']}" stroke-opacity=".14"/>
    <circle cx="53" cy="54" r="21" fill="none" stroke="{c['amber']}" stroke-opacity=".14"/>
    <circle cx="53" cy="54" r="11" fill="{c['amber']}"/>
    <circle cx="53" cy="54" r="2.2" fill="{c['disc']}"/>
    <path d="M14 99h20" stroke="{c['amber']}" stroke-width="2" stroke-linecap="round"/>
  </g>
  <g font-family="Arial, Helvetica, sans-serif" fill="{c['ink']}">{typography}</g>
  <g transform="translate({arrow_x} {arrow_y})" stroke="{c['amber']}" fill="none">
    <circle r="17" stroke-opacity=".3"/>
    <path d="M-5 5 5-5M-4-5h9v9" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
  </g>
</svg>
'''


def tool_label(theme, label, width):
    c = PALETTES[theme]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="30" viewBox="0 0 {width} 30" role="img" aria-label="{label}">
  <rect x=".5" y=".5" width="{width-1}" height="29" rx="7" fill="{c['bg']}" stroke="{c['edge']}"/>
  <text x="{width/2}" y="19.5" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="13" font-weight="600" fill="{c['amber']}">{label}</text>
</svg>
'''


if __name__ == '__main__':
    for theme in PALETTES:
        for compact in (False, True):
            stem = f'meloark-card-{theme}' + ('-small' if compact else '')
            (ASSETS / f'{stem}.svg').write_text(project_card(theme, compact))
        for slug, label, width in [('react', 'React', 74), ('typescript', 'TypeScript', 108), ('vite', 'Vite', 62)]:
            (ASSETS / f'tool-{slug}-{theme}.svg').write_text(tool_label(theme, label, width))
