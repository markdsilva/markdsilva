#!/usr/bin/env python3
"""Render the approved header. Python 3, Pillow, NumPy, Inkscape and FFmpeg.

Run: python scripts/render_header.py
Editable SVGs hold the palettes and desktop/mobile composition.
Motion matches the preview: a 12-second orbit and a quiet audio phrase.
"""
import math
from pathlib import Path
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SCALE = 2
FRAMES = 240
DURATION_MS = 50
HEIGHTS = [20, 32, 49, 67, 52, 36, 65, 88, 76, 48, 34, 53, 70, 42, 24]
ET.register_namespace('', 'http://www.w3.org/2000/svg')


def rgb(hex_color):
    return np.array([int(hex_color[i:i + 2], 16) for i in (1, 3, 5)])


def background(theme, compact):
    stem = f'header-{theme}' + ('-small' if compact else '')
    tree = ET.parse(ROOT / 'assets' / f'{stem}.svg')
    svg = tree.getroot()
    ids = {el.get('id'): el for el in svg.iter() if el.get('id')}
    size = int(svg.get('width')), int(svg.get('height'))
    transform = ids['amber-art'].get('transform')
    center = tuple(map(float, re.search(r'translate\(([^)]+)\)', transform)[1].split()))
    scale_match = re.search(r'scale\(([^)]+)\)', transform)
    art_scale = float(scale_match[1]) if scale_match else 1.0
    colors = [rgb(stop.get('stop-color')) for stop in ids['amber-bars']]
    accent = rgb(next(el.get('fill') for el in ids['amber-orbit']
                      if el.get('fill', '').startswith('#')))
    ids['amber-signal'].clear()
    ids['amber-art'].remove(ids['amber-orbit'])
    with tempfile.TemporaryDirectory() as tmp:
        source, target = Path(tmp) / 'base.svg', Path(tmp) / 'base.png'
        tree.write(source, encoding='utf-8', xml_declaration=True)
        subprocess.run(['inkscape', str(source), '--export-type=png',
                        f'--export-filename={target}', f'--export-width={size[0] * SCALE}'],
                       check=True, capture_output=True)
        matte = Image.new('RGBA', (size[0] * SCALE, size[1] * SCALE),
                          '#0d1117' if theme == 'dark' else '#ffffff')
        matte.alpha_composite(Image.open(target).convert('RGBA'))
        return matte, size, center, art_scale, colors, accent, stem


def frame(artwork, phase):
    base, size, center, art_scale, colors, accent, _ = artwork
    phase %= 1.0
    tau = 2 * math.pi
    s = SCALE * art_scale
    cx, cy = center[0] * SCALE, center[1] * SCALE
    layer = Image.new('RGBA', base.size)
    draw = ImageDraw.Draw(layer)
    for i, height in enumerate(HEIGHTS):
        h = height * (1 + .10 * math.sin(tau * phase * 3 - i * .32)
                      + .025 * math.sin(tau * phase + i * .42))
        x0, y0 = round(cx + (-72 + i * 10) * s), round(cy - h / 2 * s)
        w, pixels = max(1, round(4 * s)), max(1, round(h * s))
        mask = Image.new('L', (w, pixels))
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, pixels - 1),
                                               radius=2 * s, fill=255)
        gradient = np.zeros((pixels, w, 4), dtype=np.uint8)
        for y in range(pixels):
            ratio = y / max(1, pixels - 1)
            if ratio <= .5:
                gradient[y, :, :3] = colors[0] * (1 - ratio * 2) + colors[1] * ratio * 2
                alpha = 255
            else:
                f = (ratio - .5) * 2
                gradient[y, :, :3] = colors[1] * (1 - f) + colors[2] * f
                alpha = round(255 * (1 - .48 * f))
            gradient[y, :, 3] = alpha
        bar = Image.fromarray(gradient)
        bar.putalpha(Image.fromarray(np.minimum(gradient[:, :, 3], np.asarray(mask))))
        layer.alpha_composite(bar, (x0, y0))
    angle = -math.pi / 2 + tau * phase
    color = tuple(int(c) for c in accent)
    points = [(round(cx + 104 * s * math.cos(a)), round(cy + 104 * s * math.sin(a)))
              for a in np.linspace(angle - .52, angle, 60)]
    draw.line(points, fill=(*color, 64), width=max(1, round(1.35 * s)))
    x, y = cx + 104 * s * math.cos(angle), cy + 104 * s * math.sin(angle)
    draw.ellipse((x - 7 * s, y - 7 * s, x + 7 * s, y + 7 * s), fill=(*color, 26))
    draw.ellipse((x - 2.8 * s, y - 2.8 * s, x + 2.8 * s, y + 2.8 * s), fill=(*color, 255))
    canvas = base.copy()
    canvas.alpha_composite(layer)
    return canvas.convert('RGB').resize(size, Image.Resampling.LANCZOS)


def render(theme, compact):
    artwork = background(theme, compact)
    size, stem = artwork[1], artwork[-1]
    # Reserve colors for the small waveform instead of letting the much larger
    # stationary background consume nearly the entire GIF palette.
    base_palette = artwork[0].convert('RGB').resize(size, Image.Resampling.LANCZOS).quantize(colors=160)
    samples = []
    cx, cy = artwork[2]
    scale = artwork[3]
    for i in range(16):
        phase = i / 16
        pixels = np.asarray(frame(artwork, phase))
        for j, height in enumerate(HEIGHTS):
            h = height * (1 + .10 * math.sin(2 * math.pi * phase * 3 - j * .32)
                          + .025 * math.sin(2 * math.pi * phase + j * .42))
            x = round(cx + (-70 + j * 10) * scale)
            start, end = round(cy - h * scale / 2), round(cy + h * scale / 2)
            samples.append(pixels[start:end, max(0, x - 1):x + 1].reshape(-1, 3))
    wave_pixels = np.concatenate(samples).reshape(-1, 1, 3)
    wave_palette = Image.fromarray(wave_pixels).quantize(colors=96)
    palette = Image.new('P', (1, 1))
    palette.putpalette(base_palette.getpalette()[:160 * 3] + wave_palette.getpalette()[:96 * 3])
    # Dither smooth gradients once, then keep every stationary pixel identical
    # throughout the loop. This avoids both banding and background shimmer.
    static = artwork[0].convert('RGB').resize(size, Image.Resampling.LANCZOS)
    static_rgb = np.asarray(static)
    static_indices = np.asarray(static.quantize(palette=palette, dither=Image.Dither.FLOYDSTEINBERG))
    frames = []
    for i in range(FRAMES):
        image = frame(artwork, i / FRAMES)
        indices = np.array(image.quantize(palette=palette, dither=Image.Dither.FLOYDSTEINBERG))
        stationary = np.all(np.asarray(image) == static_rgb, axis=2)
        indices[stationary] = static_indices[stationary]
        indexed = Image.frombytes('P', size, indices.tobytes())
        indexed.putpalette(palette.getpalette())
        frames.append(indexed)
    target = ROOT / 'assets' / f'{stem}.gif'
    frames[0].save(target, save_all=True, append_images=frames[1:],
                   duration=DURATION_MS, loop=0, disposal=1, optimize=False)
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
    print(f'{target.name}: {target.stat().st_size / 1024:.0f} KB, 12 s, 20 fps', flush=True)


if __name__ == '__main__':
    for mode in ('dark', 'light'):
        for mobile in (False, True):
            render(mode, mobile)
