#!/usr/bin/env python3
"""Build wrapped title glyphs for every supported language from the official client bitmaps (requires Pillow)."""
import argparse
import io
import json
import math
import zipfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'resourcepack/assets/biomevisible'
# The title shader scales the block by its pixel size, so the block geometry is fixed.
CARD_WIDTH = 266
CELL_WIDTH = CARD_WIDTH // 2
CARD_HEIGHT = 68
# Language order fixes every atlas range in the Private Use Area: index * 67 * 2 glyphs.
HEADINGS = {
    'en_us': 'new biome discovered',
    'ru_ru': 'открыт новый биом',
    'de_de': 'Neues Biom entdeckt',
    'fr_fr': 'Nouveau biome découvert',
    'es_es': 'Nuevo bioma descubierto',
    'it_it': 'Nuovo bioma scoperto',
    'pl_pl': 'Odkryto nowy biom',
    'nl_nl': 'Nieuw bioom ontdekt',
    'pt_br': 'Novo bioma descoberto',
}
EXTRA_LANGUAGES = tuple(language for language in HEADINGS if language not in ('en_us', 'ru_ru'))


def build(client_jar, ru_lang, lang_dir):
    outputs = {}
    with zipfile.ZipFile(client_jar) as client:
        languages = {
            'en_us': json.loads(client.read('assets/minecraft/lang/en_us.json')),
            'ru_ru': json.loads(ru_lang.read_text(encoding='utf-8')),
        }
        for language in EXTRA_LANGUAGES:
            path = lang_dir / f'{language}.json'
            if not path.exists():
                raise SystemExit(f'Missing official translations: {path}')
            languages[language] = json.loads(path.read_text(encoding='utf-8'))
        biomes = sorted(p.stem for p in (ROOT / 'datapack/data/biomevisible/advancement/biome').glob('*.json'))
        glyphs = {}
        providers = json.loads(client.read('assets/minecraft/font/include/default.json'))['providers']
        for provider in providers:
            if provider.get('type') != 'bitmap':
                continue
            namespace, file = provider['file'].split(':')
            image = Image.open(io.BytesIO(client.read(f'assets/{namespace}/textures/{file}'))).convert('RGBA')
            rows = provider['chars']
            width, height = image.width // len(rows[0]), image.height // len(rows)
            for y, row in enumerate(rows):
                for x, char in enumerate(row):
                    if char == '\0' or char in glyphs:
                        continue
                    tile = image.crop((x * width, y * height, (x + 1) * width, (y + 1) * height))
                    bounds = tile.getchannel('A').getbbox()
                    if bounds:
                        # Vanilla glyph advance includes one pixel after the rightmost ink.
                        ink_width = bounds[2]
                        tile = tile.crop((0, 0, ink_width, height))
                        tile = tile.resize((round(ink_width * provider.get('height', 8) / height), provider.get('height', 8)), Image.Resampling.NEAREST)
                        glyphs[char] = (tile, provider['ascent'])
        pin = Image.open(ASSETS / 'textures/font/pin.png').convert('RGBA')

        def text_image(text):
            advances = [4 if c == ' ' else glyphs[c][0].width + 1 for c in text]
            result = Image.new('RGBA', (sum(advances) - 1, 12))
            x = 0
            for char, advance in zip(text, advances):
                if char != ' ':
                    tile, ascent = glyphs[char]
                    result.alpha_composite(tile, (x, 10 - ascent))
                x += advance
            return result

        cards = {}
        for language, translations in languages.items():
            header = text_image(HEADINGS[language])
            heading = Image.new('RGBA', (header.width + 12, 12))
            heading.alpha_composite(header)
            heading.alpha_composite(pin, (header.width + 4, 3))
            for biome in biomes:
                words = translations[f'biome.minecraft.{biome}'].split()
                # The block holds two lines, so names longer than four words wrap after half of them rounded up.
                per_line = max(2, (len(words) + 1) // 2)
                lines = [text_image(' '.join(words[i:i + per_line])) for i in range(0, len(words), per_line)]
                lines = [line.resize((line.width * 2, 24), Image.Resampling.NEAREST) for line in lines]
                width = max(heading.width, *(line.width for line in lines))
                card = Image.new('RGBA', (width, 14 + 27 * len(lines)))
                card.alpha_composite(heading, ((width - heading.width) // 2, 0))
                for i, line in enumerate(lines):
                    card.alpha_composite(line, ((width - line.width) // 2, 14 + 27 * i))
                cards[language, biome] = card

        cell_width, cell_height = CELL_WIDTH, CARD_HEIGHT
        for (language, biome), card in sorted(cards.items()):
            assert card.width <= CARD_WIDTH and card.height <= CARD_HEIGHT, (
                f'{language} {biome} needs a {card.width}x{card.height} block, '
                f'but the shader only supports {CARD_WIDTH}x{CARD_HEIGHT}'
            )
        font_providers = [{'type': 'space', 'advances': {'\uf000': -1}}]
        for language_index, language in enumerate(languages):
            atlas = Image.new('RGBA', (cell_width * 8, cell_height * math.ceil(len(biomes) * 2 / 8)))
            chars = []
            lang_path = ASSETS / f'lang/{language}.json'
            lang = json.loads(lang_path.read_text(encoding='utf-8')) if lang_path.exists() else {}
            # Keep descriptions; regenerate only the title translation keys.
            lang = {key: value for key, value in lang.items() if not key.startswith('biomevisible.title.')}
            for i, biome in enumerate(biomes):
                # Two glyphs keep the 2x biome pixels within Minecraft's 256px font atlas.
                card = Image.new('RGBA', (CARD_WIDTH, cell_height))
                source = cards[language, biome]
                card.alpha_composite(source, ((CARD_WIDTH - source.width) // 2, 0))
                title_chars = []
                for half in range(2):
                    index = i * 2 + half
                    char = chr(0xE000 + language_index * len(biomes) * 2 + index)
                    title_chars.append(char + '\uf000')
                    if index % 8 == 0:
                        chars.append('')
                    chars[-1] += char
                    tile = card.crop((half * cell_width, 0, (half + 1) * cell_width, cell_height))
                    # Nonzero alpha fixes the glyph advance; the fragment shader discards it.
                    tile.putpixel((cell_width - 1, cell_height - 1), (255, 255, 255, 1))
                    atlas.alpha_composite(tile, ((index % 8) * cell_width, (index // 8) * cell_height))
                lang[f'biomevisible.title.biome.minecraft.{biome}'] = ''.join(title_chars)
            chars[-1] = chars[-1].ljust(8, '\0')
            png = io.BytesIO()
            atlas.save(png, format='PNG')
            outputs[ASSETS / f'textures/font/titles_{language}.png'] = png.getvalue()
            outputs[lang_path] = (json.dumps(lang, ensure_ascii=False, indent=2) + '\n').encode()
            font_providers.append({'type': 'bitmap', 'file': f'biomevisible:font/titles_{language}.png', 'height': cell_height, 'ascent': 7, 'chars': chars})
        outputs[ASSETS / 'font/title.json'] = (json.dumps({'providers': font_providers}, ensure_ascii=False, indent=2) + '\n').encode()
    return outputs


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('client_jar', type=Path)
    parser.add_argument('--ru-lang', type=Path, required=True)
    parser.add_argument('--lang-dir', type=Path, required=True,
                        help='Directory holding the official <locale>.json files of every language except en_us and ru_ru')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for path, content in build(args.client_jar, args.ru_lang, args.lang_dir).items():
        if args.check:
            if not path.exists() or path.read_bytes() != content:
                raise SystemExit(f'Stale title asset: {path.relative_to(ROOT)}')
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    print(f'OK: 67 titles in {len(HEADINGS)} languages ({", ".join(HEADINGS)}), '
          'at most two lines per biome title' + ('; generated assets match' if args.check else ''))
