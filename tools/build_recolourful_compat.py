#!/usr/bin/env python3
"""Build BiomeVisible's adapter for installed Recolourful DARK 3.1.4, Minecraft 26.3.

The original Recolourful pack must stay enabled below this variant. This archive
contains our vertex shader and assets; its shader library and fragment shader are
resolved from the installed Recolourful pack at runtime.
"""
import argparse
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHADERS = 'assets/minecraft/shaders/'


def build(output, root=ROOT):
    vertex = (root / 'resourcepack' / (SHADERS + 'core/text.vsh')).read_text()
    vertex = vertex.replace('#include <minecraft:globals.glsl>',
                            '#include <minecraft:globals.glsl>\n#define USE_RED_CHANNEL\n'
                            '#include <minecraft:interfaces.glsl>')
    vertex = vertex.replace('void main() {',
                            'uniform sampler2D Sampler0;\n'
                            'layout(location = 4) out float interpFactor;\n'
                            'layout(location = 5) out vec2 texCoordNext;\n\n'
                            'void main() {\n'
                            '    Data recolourful = rendertype_text(ProjMat, GameTime, Sampler0, Position, UV0, Color);')
    vertex = vertex.replace('vec4(Position, 1.0)', 'vec4(recolourful.position, 1.0)')
    vertex = vertex.replace('fog_spherical_distance(Position)', 'fog_spherical_distance(recolourful.position)')
    vertex = vertex.replace('fog_cylindrical_distance(Position)', 'fog_cylindrical_distance(recolourful.position)')
    vertex = vertex.replace('vertexColor = Color', 'vertexColor = recolourful.color')
    vertex = vertex.replace('texCoord0 = UV0;',
                            'texCoord0 = recolourful.uv0;\n'
                            '    interpFactor = recolourful.interpFactor;\n'
                            '    texCoordNext = recolourful.texCoordNext;')
    metadata = json.loads((root / 'resourcepack/pack.mcmeta').read_text())
    metadata['pack']['description'] = (
        f"BiomeVisible v{metadata['version']}: requires Recolourful DARK 3.1.4 (26.3); enable above it")
    overrides = {
        'pack.mcmeta': (json.dumps(metadata, indent=2) + '\n').encode(),
        SHADERS + 'core/text.vsh': vertex.encode(),
    }
    # Let Minecraft resolve the matching fragment shader from Recolourful below us.
    excluded = {SHADERS + 'core/text.fsh'}
    tracked = subprocess.check_output(['git', 'ls-files', '-z', '--', 'resourcepack'], cwd=root).decode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for name in filter(None, tracked.split('\0')):
            path = Path(name).relative_to('resourcepack').as_posix()
            if path not in overrides and path not in excluded:
                bundle.write(root / name, path)
        for path, content in overrides.items():
            bundle.writestr(path, content)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.output)
    print(f'OK: {args.output}; enable above the original Recolourful pack, replacing regular BiomeVisible')
