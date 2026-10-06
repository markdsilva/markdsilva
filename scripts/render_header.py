#!/usr/bin/env python3
"""Render the profile header. Requires Python 3, Pillow, NumPy, Inkscape and FFmpeg.

Run from any directory: python scripts/render_header.py
SVGs remain the editable, static alternatives. All motion is periodic over 8 s.
Amber #FAA544 and orange #F18029 are sampled from the existing profile avatar;
the light version uses its copper #B1522F for contrast.
"""

import math
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SIZE = (960, 320)
SCALE = 2
FRAMES = 160
DURATION_MS = 50
HEIGHTS = [22, 36, 56, 82, 112, 68, 40, 92, 136, 100, 60, 32, 48, 76, 104, 64, 36]
SVG_NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', SVG_NS)


def background(theme):
    """Rasterize the source artwork without its static waveform or orbit dots."""
    tree = ET.parse(ROOT / 'assets' / f'header-{theme}.svg')
    for parent in tree.getroot().iter():
        for child in list(parent):
            is_wave = child.tag == f'{{{SVG_NS}}}g' and child.get('fill') == 'url(#wave)'
            is_dot = child.tag == f'{{{SVG_NS}}}circle' and child.get('cx') in ('800', '694') and child.get('r') == '4'
            if is_wave or is_dot:
                parent.remove(child)
    with tempfile.TemporaryDirectory() as tmp:
        source, target = Path(tmp) / 'base.svg', Path(tmp) / 'base.png'
        tree.write(source, encoding='utf-8', xml_declaration=True)
        subprocess.run([
            'inkscape', str(source), '--export-type=png',
            f'--export-filename={target}', f'--export-width={SIZE[0] * SCALE}',
        ], check=True, capture_output=True)
        # Opaque corners prevent GIF transparency/disposal artifacts.
        matte = Image.new('RGBA', (SIZE[0] * SCALE, SIZE[1] * SCALE),
                          '#0d1117' if theme == 'dark' else '#ffffff')
        matte.alpha_composite(Image.open(target).convert('RGBA'))
        return matte.convert('RGB')


def frame(base, theme, phase):
    phase %= 1.0
    tau = 2 * math.pi
    color = (250, 165, 68) if theme == 'dark' else (177, 82, 47)
    orange = (241, 128, 41) if theme == 'dark' else color
    canvas = base.copy().convert('RGBA')
    layer = Image.new('RGBA', canvas.size)
    draw = ImageDraw.Draw(layer)

    # A coherent traveling phrase, with small secondary movement. Integer
    # frequencies ensure the last-to-first transition is another normal step.
    for i, height in enumerate(HEIGHTS):
        modulation = 1 + .105 * math.sin(tau * 2 * phase - i * .36) + .035 * math.sin(tau * phase + i * .53)
        h = height * modulation
        x0, y0 = round((686 + 13 * i) * SCALE), round((160 - h / 2) * SCALE)
        w, pixels = 5 * SCALE, max(1, round(h * SCALE))
        mask = Image.new('L', (w, pixels))
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, pixels - 1), radius=2.5 * SCALE, fill=255)
        gradient = np.zeros((pixels, w, 4), dtype=np.uint8)
        for y in range(pixels):
            ratio = y / max(1, pixels - 1)
            gradient[y, :, :3] = np.asarray(color) * (1 - ratio * .45) + np.asarray(orange) * ratio * .45
            gradient[y, :, 3] = round(255 * (1 - .52 * ratio))
        bar = Image.fromarray(gradient)
        bar.putalpha(Image.fromarray(np.minimum(gradient[:, :, 3], np.asarray(mask))))
        layer.alpha_composite(bar, (x0, y0))

    # One quiet orbit with a short, tapering tail. The rings themselves stay still.
    angle = -math.pi / 2 + tau * phase
    for j in range(18):
        a = angle - (18 - j) * .012
        b = a + .012
        p = [(round((800 + 136 * math.cos(v)) * SCALE),
              round((160 + 136 * math.sin(v)) * SCALE)) for v in (a, b)]
        draw.line(p, fill=(*color, round(65 * (j + 1) / 18)), width=SCALE)
    x, y = (800 + 136 * math.cos(angle)) * SCALE, (160 + 136 * math.sin(angle)) * SCALE
    draw.ellipse((x - 7 * SCALE, y - 7 * SCALE, x + 7 * SCALE, y + 7 * SCALE), fill=(*color, 15))
    draw.ellipse((x - 3.5 * SCALE, y - 3.5 * SCALE, x + 3.5 * SCALE, y + 3.5 * SCALE), fill=(*color, 255))
    canvas.alpha_composite(layer)
    return canvas.convert('RGB').resize(SIZE, Image.Resampling.LANCZOS)


def render(theme):
    base = background(theme)
    # One palette for every frame keeps static type and background stable.
    swatches = Image.new('RGB', (SIZE[0], SIZE[1] * 12))
    for i in range(12):
        swatches.paste(frame(base, theme, i / 12), (0, i * SIZE[1]))
    palette = swatches.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    frames = [frame(base, theme, i / FRAMES).quantize(palette=palette, dither=Image.Dither.NONE)
              for i in range(FRAMES)]
    target = ROOT / 'assets' / f'header-{theme}.gif'
    frames[0].save(target, save_all=True, append_images=frames[1:],
                   duration=DURATION_MS, loop=0, disposal=1, optimize=False)
    # Transparent frame differences avoid re-encoding the stationary rings.
    with tempfile.TemporaryDirectory() as tmp:
        optimized = Path(tmp) / 'optimized.gif'
        subprocess.run([
            'ffmpeg', '-v', 'error', '-i', str(target), '-filter_complex',
            '[0:v]split[a][b];[a]palettegen=stats_mode=diff:max_colors=256[p];'
            '[b][p]paletteuse=dither=none:diff_mode=rectangle',
            '-gifflags', '+offsetting+transdiff', '-loop', '0',
            '-final_delay', str(DURATION_MS // 10), str(optimized),
        ], check=True)
        target.write_bytes(optimized.read_bytes())
    print(f'{target.name}: {target.stat().st_size / 1024:.0f} KB, 8 s, 20 fps')


if __name__ == '__main__':
    for mode in ('dark', 'light'):
        render(mode)
