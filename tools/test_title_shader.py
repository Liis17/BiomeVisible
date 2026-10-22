#!/usr/bin/env python3
"""Run the actual text shaders on OpenGL (requires ModernGL and an official client jar)."""
import argparse
from contextlib import contextmanager
import math
import re
import struct
import unittest
import zipfile
from pathlib import Path

import moderngl

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('client_jar', type=Path)
parser.add_argument('--resource-pack', type=Path, help='Test a generated compatibility ZIP instead')
parser.add_argument('--recolourful', type=Path, help='Installed DARK 3.1.4 ZIP, enabled below the adapter for this test')
args = parser.parse_args()
if args.recolourful and not args.resource_pack:
    parser.error('--recolourful requires --resource-pack')
client = zipfile.ZipFile(args.client_jar)
pack = zipfile.ZipFile(args.resource_pack) if args.resource_pack else None
recolourful = zipfile.ZipFile(args.recolourful) if args.recolourful else None
ctx = moderngl.create_standalone_context(require=330)
ctx.simple_framebuffer((1, 1)).use()
ctx.texture((1, 1), 4, bytes([255] * 4)).use(0)


def resource(path):
    if pack and path in pack.namelist():
        return pack.read(path).decode()
    if recolourful:
        for candidate in ('26.3/' + path, path):
            if candidate in recolourful.namelist():
                return recolourful.read(candidate).decode()
    local = ROOT / 'resourcepack' / path
    if not pack and local.exists():
        return local.read_text()
    return client.read(path).decode()


def shader(stage, defines, source=None):
    def expand(source):
        def include(match):
            namespace, path = match[1].split(':')
            return expand(resource(f'assets/{namespace}/shaders/include/{path}'))
        return re.sub(r'#include <([^>]+)>', include, source)
    if source is None:
        source = resource(f'assets/minecraft/shaders/core/text.{stage}')
    return expand(source.replace('#version 330', '#version 330\n' + '\n'.join(
        f'#define {define}' for define in defines)))


def program(defines):
    return ctx.program(vertex_shader=shader('vsh', defines),
                       fragment_shader=shader('fsh', defines), varyings=['gl_Position'])


@contextmanager
def releasing(obj):
    try:
        yield obj
    finally:
        obj.release()


class TitleShaderTest(unittest.TestCase):
    def test_pack_supplies_a_matching_fragment_shader(self):
        path = 'assets/minecraft/shaders/core/text.fsh'
        if recolourful:
            self.assertNotIn(path, pack.namelist(), 'The adapter must inherit the fragment shader from Recolourful')
            self.assertNotIn('assets/minecraft/shaders/include/interfaces.glsl', pack.namelist(),
                             'The adapter must not distribute the Recolourful library')
            self.assertEqual(resource(path), recolourful.read('26.3/' + path).decode())
            return
        self.assertTrue(path in pack.namelist() if pack else (ROOT / 'resourcepack' / path).exists(),
                        'Replacing only text.vsh mixes incompatible shaders from other packs')

    def test_text_pipeline_variants_link(self):
        for defines in [[], ['IS_SEE_THROUGH'], ['IS_GUI'], ['IS_GUI', 'IS_GRAYSCALE']]:
            with self.subTest(defines=defines):
                program(defines).release()

    @unittest.skipUnless(recolourful, 'Only the adapter delegates rendering to Recolourful')
    def test_recolourful_sprite_outputs_match_the_original_shader(self):
        original = recolourful.read('26.3/assets/minecraft/shaders/core/text.vsh').decode()
        varyings = ['gl_Position', 'vertexColor', 'texCoord0', 'interpFactor', 'texCoordNext']
        identity = [1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1.]
        projection = identity.copy()
        projection[0], projection[5], projection[12], projection[13] = 2 / 320, -2 / 240, -1., 1.
        blocks = {
            'DynamicTransforms': struct.pack('40f', *identity, *identity, *([1.] * 4), *([0.] * 4)),
            'Projection': struct.pack('16f', *projection),
            'Globals': struct.pack('8f2f2i', *([0.] * 7), .001, 320., 240., 0, 0),
        }
        buffers = [ctx.buffer(content) for content in blocks.values()]
        programs = [ctx.program(vertex_shader=source, fragment_shader=shader('fsh', ['IS_GUI']), varyings=varyings)
                    for source in [shader('vsh', ['IS_GUI']), shader('vsh', ['IS_GUI'], original)]]
        try:
            for prog in programs:
                for binding, (name, buffer) in enumerate(zip(blocks, buffers)):
                    if name in prog:
                        prog[name].binding = binding
                        buffer.bind_to_uniform_block(binding)
            data = struct.pack('9f', 160., 120., 0., *([64 / 255] * 3), 1., 0., 0.)
            baseline = None
            changed = False
            # Synthetic sprite metadata exercises the library's red-channel corner encoding.
            sprites = [(255, 255, 255, 255)] + [(corner, group, 1, 2)
                                               for corner in range(1, 5) for group in (2, 3, 5)]
            for sprite in sprites:
                with self.subTest(sprite=sprite), releasing(ctx.texture((1, 1), 4, bytes(sprite))) as texture:
                    texture.use(0)
                    results = []
                    for prog in programs:
                        with releasing(ctx.buffer(data)) as vertex, releasing(ctx.buffer(reserve=52)) as output:
                            with releasing(ctx.vertex_array(prog, [(vertex, '3f 4f 2f', 'Position', 'Color', 'UV0')])) as vao:
                                vao.transform(output, vertices=1, mode=moderngl.POINTS)
                            results.append(struct.unpack('13f', output.read()))
                    for actual, expected in zip(*results):
                        self.assertAlmostEqual(actual, expected, delta=.00001)
                    if baseline is None:
                        baseline = results[1]
                    changed |= results[1] != baseline
            self.assertTrue(changed, 'The fixtures must exercise Recolourful sprite changes')
        finally:
            for obj in programs + buffers:
                obj.release()
            ctx.texture((1, 1), 4, bytes([255] * 4)).use(0)

    def test_notifications_fit_at_the_top_and_other_text_stays_put(self):
        identity = [1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1.]
        with releasing(program(['IS_GUI'])) as prog:
            for width, height in [(320, 240), (854, 480), (1710, 1112), (1709, 1111), (2048, 1174)]:
                for scale in range(1, 5):
                    if width / scale < 320 or height / scale < 240:
                        continue
                    gui = [math.ceil(width / scale), math.ceil(height / scale)]
                    center = [math.floor(value / 2) for value in gui]
                    model = identity.copy()
                    model[0] = model[5] = 4.
                    model[12], model[13] = center[0], center[1] - 40.
                    projection = identity.copy()
                    projection[0], projection[5] = 2. / gui[0], -2. / gui[1]
                    projection[12], projection[13] = -1., 1.
                    blocks = {
                        'DynamicTransforms': struct.pack('40f', *model, *identity, *([1.] * 4), *([0.] * 4)),
                        'Projection': struct.pack('16f', *projection),
                        'Globals': struct.pack('8f2f2i', *([0.] * 8), float(width), float(height), 0, 0),
                    }
                    buffers = []
                    for binding, (name, content) in enumerate(blocks.items()):
                        if name in prog:
                            prog[name].binding = binding
                            buffer = ctx.buffer(content)
                            buffer.bind_to_uniform_block(binding)
                            buffers.append(buffer)
                    for color in [(255, 255, 254), (255, 122, 92), (196, 181, 253),
                                  (63, 63, 62), (58, 26, 18), (30, 27, 46), (255, 255, 255)]:
                        with self.subTest(window=(width, height), scale=scale, color=color):
                            vertices = [(-133., 0.), (133., 0.), (-133., 68.)]
                            data = b''.join(struct.pack('9f', x, y, 0., *(c / 255 for c in color), 1., 0., 0.)
                                            for x, y in vertices)
                            with releasing(ctx.buffer(data)) as vertex, releasing(ctx.buffer(reserve=48)) as output:
                                with releasing(ctx.vertex_array(prog, [(vertex, '3f 4f 2f', 'Position', 'Color', 'UV0')])) as vao:
                                    vao.transform(output, vertices=3)
                                clip = struct.unpack('12f', output.read())
                            points = [((clip[i] + 1) * width / 2, (1 - clip[i + 1]) * height / 2)
                                      for i in range(0, 12, 4)]
                            if color == (255, 255, 255):
                                for (x, y), (actual_x, actual_y) in zip(vertices, points):
                                    self.assertAlmostEqual(actual_x, (center[0] + x * 4) * width / gui[0], delta=.01)
                                    self.assertAlmostEqual(actual_y, (center[1] - 40 + y * 4) * height / gui[1], delta=.01)
                                continue
                            card_width = points[1][0] - points[0][0]
                            card_height = points[2][1] - points[0][1]
                            self.assertLessEqual(card_width, max(266., width * .7) + .01)
                            self.assertLessEqual(card_height, max(68., height * .3) + .01)
                            self.assertAlmostEqual(points[0][1], math.floor(12 * height / gui[1] + .5), delta=.01)
                            self.assertAlmostEqual((points[0][0] + points[1][0]) / 2,
                                                   center[0] * width / gui[0], delta=.501)
                            texel = card_width / 266
                            self.assertAlmostEqual(texel, round(texel), delta=.001)
                            self.assertAlmostEqual(card_height / 68, texel, delta=.001)
                    for buffer in buffers:
                        buffer.release()


if __name__ == '__main__':
    unittest.main(argv=['test_title_shader.py'])
