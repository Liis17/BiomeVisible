#!/usr/bin/env python3
"""Validate shared versions and package changed packs since a published release."""

import argparse
import json
import re
import subprocess
import zipfile
from pathlib import Path


PACKS = ("datapack", "resourcepack")


def git(*args):
    return subprocess.check_output(["git", *args])


def version(metadata):
    value = metadata.get("version", "")
    if not isinstance(value, str) or not re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", value):
        raise SystemExit("pack.mcmeta version must use MAJOR.MINOR.PATCH")
    return tuple(map(int, value.split(".")))


def build(previous_tag, output_dir):
    metadata = {pack: json.loads(Path(pack, "pack.mcmeta").read_text()) for pack in PACKS}
    versions = {pack: version(meta) for pack, meta in metadata.items()}
    if len(set(versions.values())) != 1:
        raise SystemExit("Datapack and resource pack versions must match")
    current_version = metadata["datapack"]["version"]
    for pack, meta in metadata.items():
        if meta["pack"]["description"]["with"] != [current_version]:
            raise SystemExit(f"{pack} description must display version {current_version}")

    if previous_tag:
        # Reject old queued runs or rewritten release history instead of releasing backwards.
        subprocess.run(["git", "merge-base", "--is-ancestor", previous_tag, "HEAD"], check=True)
        paths = git("diff", "--name-only", "-z", previous_tag, "HEAD", "--", *PACKS).decode().split("\0")
        changed = [pack for pack in PACKS if any(path.startswith(pack + "/") for path in paths)]
    else:
        changed = list(PACKS)
    if not changed:
        return {"release": "false"}

    if previous_tag:
        for pack in PACKS:
            previous = json.loads(git("show", f"{previous_tag}:{pack}/pack.mcmeta"))
            if versions[pack] <= version(previous):
                raise SystemExit("Changes to either pack require a higher version in both packs")

    output_dir.mkdir(parents=True, exist_ok=True)
    archives = []
    for pack in changed:
        archive = output_dir / f"BiomeVisible-{pack}-{current_version}.zip"
        # Only tracked files belong in a release; omit local files such as .DS_Store.
        paths = git("ls-files", "-z", "--", pack).decode().split("\0")
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            for name in sorted(filter(None, paths)):
                path = Path(name)
                bundle.write(path, path.relative_to(pack).as_posix())
        archives.append(archive.name)

    commit_range = f"{previous_tag}..HEAD" if previous_tag else "HEAD"
    commits = git("log", "--reverse", "--format=- %h %s", commit_range).decode().rstrip()
    notes = f"BiomeVisible v{current_version}\n\n## Downloads\n\n"
    notes += "\n".join(f"- `{name}`" for name in archives)
    notes += "\n\n## Commits since " + (f"`{previous_tag}`" if previous_tag else "the start of the project")
    notes += f"\n\n{commits}\n"
    (output_dir / "release-notes.md").write_text(notes, encoding="utf-8")
    return {"release": "true", "version": current_version, "tag": f"v{current_version}"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous-tag", default="")
    parser.add_argument("--output-dir", type=Path, default=Path("dist"))
    args = parser.parse_args()
    for key, value in build(args.previous_tag, args.output_dir).items():
        print(f"{key}={value}")
