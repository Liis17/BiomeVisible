#!/usr/bin/env python3
"""Build a local BiomeVisible variant for Recolourful Containers DARK 3.1.4, Minecraft 26.3.

The original Recolourful pack must stay enabled below this variant. Its shaders are
read from the supplied ZIP, rather than distributed with BiomeVisible releases.
"""
import argparse
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHADERS = 'assets/minecraft/shaders/'


def build(recolourful, output):
    with zipfile.ZipFile(recolourful) as source:
        vertex = source.read('26.3/' + SHADERS + 'core/text.vsh').decode()
        fragment = source.read('26.3/' + SHADERS + 'core/text.fsh')
        interface = source.read(SHADERS + 'include/interfaces.glsl')
    target = '    gl_Position = ProjMat * ModelViewMat * vec4(data.position, 1.0);'
    if vertex.count(target) != 1 or 'layout(location = 4) out float interpFactor;' not in vertex:
        raise ValueError('Unsupported Recolourful text shader; expected DARK 3.1.4 for 26.3')
    own = (ROOT / 'resourcepack' / (SHADERS + 'core/text.vsh')).read_text()
    # Reuse the actual positioning code; preserve all Recolourful data and outputs.
    positioning = own.split('void main() {\n', 1)[1].split('    gl_Position =', 1)[0]
    positioning = positioning.replace('vec4(Position, 1.0)', 'vec4(data.position, 1.0)')
    vertex = vertex.replace(target, positioning + '    gl_Position = ProjMat * position;')
    metadata = json.loads((ROOT / 'resourcepack/pack.mcmeta').read_text())
    metadata['pack']['description'] = f"BiomeVisible v{metadata['version']} + Recolourful DARK 3.1.4 (26.3)"
    overrides = {
        'pack.mcmeta': (json.dumps(metadata, indent=2) + '\n').encode(),
        SHADERS + 'core/text.vsh': vertex.encode(),
        SHADERS + 'core/text.fsh': fragment,
        SHADERS + 'include/interfaces.glsl': interface,
    }
    tracked = subprocess.check_output(['git', 'ls-files', '-z', '--', 'resourcepack'], cwd=ROOT).decode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for name in filter(None, tracked.split('\0')):
            path = Path(name).relative_to('resourcepack').as_posix()
            if path not in overrides:
                bundle.write(ROOT / name, path)
        for path, content in overrides.items():
            bundle.writestr(path, content)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('recolourful', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.recolourful, args.output)
    print(f'OK: {args.output}; enable above the original Recolourful pack, replacing regular BiomeVisible')
