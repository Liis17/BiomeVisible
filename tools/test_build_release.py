#!/usr/bin/env python3
"""Exercise release packaging in an isolated Git repository without publishing."""

import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

SCRIPT = Path(__file__).with_name("build_release.py").resolve()


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Release test")
        for pack in ("datapack", "resourcepack"):
            (self.root / pack).mkdir()
            (self.root / pack / "pack.png").write_bytes(b"icon")
        self.write_versions("1.0.0")
        self.commit("Initial packs")

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.root)

    def commit(self, message):
        self.git("add", ".")
        self.git("commit", "-qm", message)

    def write_versions(self, value, resource_value=None):
        for pack, pack_version in (("datapack", value), ("resourcepack", resource_value or value)):
            meta = {"version": pack_version, "pack": {"description": {"with": [pack_version]}}}
            (self.root / pack / "pack.mcmeta").write_text(json.dumps(meta))

    def build(self, previous="", success=True):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--previous-tag", previous, "--output-dir", str(self.root / "dist")],
            cwd=self.root, text=True, capture_output=True,
        )
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def test_first_release_archives_and_all_commits(self):
        (self.root / "datapack" / ".DS_Store").write_text("untracked")
        result = self.build()
        self.assertIn("tag=v1.0.0", result.stdout)
        for pack in ("datapack", "resourcepack"):
            with zipfile.ZipFile(self.root / "dist" / f"BiomeVisible-{pack}-1.0.0.zip") as archive:
                self.assertEqual(set(archive.namelist()), {"pack.mcmeta", "pack.png"})
                self.assertEqual(json.loads(archive.read("pack.mcmeta"))["version"], "1.0.0")
        self.assertIn("Initial packs", (self.root / "dist" / "release-notes.md").read_text())

    def test_unchanged_and_unrelated_changes_skip_release(self):
        self.git("tag", "v1.0.0")
        self.assertEqual(self.build("v1.0.0").stdout.strip(), "release=false")
        (self.root / "notes.md").write_text("Unrelated")
        self.commit("Update notes")
        self.assertEqual(self.build("v1.0.0").stdout.strip(), "release=false")
        self.assertFalse((self.root / "dist").exists())

    def test_each_pack_change_requires_shared_bump(self):
        self.git("tag", "v1.0.0")
        for pack in ("datapack", "resourcepack"):
            with self.subTest(pack=pack):
                (self.root / pack / "content.txt").write_text("changed")
                self.commit(f"Update {pack}")
                result = self.build("v1.0.0", success=False)
                self.assertIn("higher version in both packs", result.stderr)
                self.git("reset", "--hard", "v1.0.0")

    def test_bumped_release_notes_include_only_new_commits(self):
        self.git("tag", "v1.0.0")
        (self.root / "notes.md").write_text("Unrelated but part of the changelog")
        self.commit("Update notes")
        self.write_versions("1.0.1")
        self.commit("Update resource pack and shared version")
        self.assertIn("tag=v1.0.1", self.build("v1.0.0").stdout)
        self.assertEqual(len(list((self.root / "dist").glob("*.zip"))), 2)
        notes = (self.root / "dist" / "release-notes.md").read_text()
        self.assertIn("Update notes", notes)
        self.assertIn("Update resource pack", notes)
        self.assertNotIn("Initial packs", notes)
        self.git("tag", "v1.0.1")
        self.assertEqual(self.build("v1.0.1").stdout.strip(), "release=false")

    def test_mismatched_invalid_or_stale_display_versions_fail(self):
        self.write_versions("1.0.1", "1.0.0")
        self.assertIn("versions must match", self.build(success=False).stderr)
        self.write_versions("01.0.0")
        self.assertIn("MAJOR.MINOR.PATCH", self.build(success=False).stderr)
        self.write_versions("1.0.1")
        path = self.root / "datapack" / "pack.mcmeta"
        meta = json.loads(path.read_text())
        meta["pack"]["description"]["with"] = ["1.0.0"]
        path.write_text(json.dumps(meta))
        self.assertIn("description must display", self.build(success=False).stderr)


if __name__ == "__main__":
    unittest.main()
