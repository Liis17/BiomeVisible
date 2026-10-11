#!/usr/bin/env python3
"""Regression check: biome strokes must retain uniformly sized source pixels (Pillow)."""
import json
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


class TitlePixelsTest(unittest.TestCase):
    def test_deep_dark_pixels_are_uniform_two_by_two_blocks(self):
        assets = ROOT / 'resourcepack/assets/biomevisible'
        font = json.loads((assets / 'font/title.json').read_text())
        lang = json.loads((assets / 'lang/en_us.json').read_text())
        rendered = []
        cursor = 0
        for char in lang['biomevisible.title.biome.minecraft.deep_dark']:
            for provider in font['providers']:
                if provider['type'] == 'space' and char in provider['advances']:
                    cursor += provider['advances'][char]
                    break
                if provider['type'] != 'bitmap':
                    continue
                rows = provider['chars']
                for y, row in enumerate(rows):
                    if char not in row:
                        continue
                    image = Image.open(assets / ('textures/' + provider['file'].split(':')[1]))
                    width, height = image.width // len(row), image.height // len(rows)
                    x = row.index(char)
                    tile = image.crop((x * width, y * height, (x + 1) * width, (y + 1) * height))
                    rendered.append((cursor, tile))
                    # Bitmap providers use the last nonzero-alpha column plus one for advance.
                    cursor += tile.getchannel('A').getbbox()[2] + 1
        card = Image.new('RGBA', (cursor, rendered[0][1].height))
        for x, part in rendered:
            card.alpha_composite(part, (x, 0))
        mask = card.getchannel('A').point(lambda value: 255 if value >= 26 else 0)
        body = mask.crop((0, 14, mask.width, mask.height))
        body = body.crop(body.getbbox())
        self.assertEqual(body.width % 2, 0, 'Uneven horizontal pixel scaling')
        self.assertEqual(body.height % 2, 0, 'Uneven vertical pixel scaling')
        for y in range(0, body.height, 2):
            for x in range(0, body.width, 2):
                self.assertEqual(len(set(body.crop((x, y, x + 2, y + 2)).tobytes())), 1,
                                 f'Unequal source pixel at ({x}, {y})')


if __name__ == '__main__':
    unittest.main()
