#!/usr/bin/env python3
"""Check BiomeVisible's data-pack files against an official 26.3 client jar."""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from collections import Counter
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


parser = argparse.ArgumentParser()
parser.add_argument("client_jar", type=Path, help="Official Minecraft 26.3 client.jar")
args = parser.parse_args()

with zipfile.ZipFile(args.client_jar) as client:
    version = json.loads(client.read("version.json"))
    require(version["id"] == "26.3", "Expected the Minecraft 26.3 client jar")
    require(version["pack_version"]["data_major"] == 121, "Expected data format 121")

    biome_prefix = "data/minecraft/worldgen/biome/"
    biomes = sorted(
        name[len(biome_prefix) : -5]
        for name in client.namelist()
        if name.startswith(biome_prefix) and name.endswith(".json")
    )
    require(len(biomes) == 67, f"Expected 67 vanilla biomes, found {len(biomes)}")
    translations = json.loads(client.read("assets/minecraft/lang/en_us.json"))
    missing_translations = [
        biome for biome in biomes if f"biome.minecraft.{biome}" not in translations
    ]
    require(not missing_translations, f"Missing vanilla translations: {missing_translations}")

repo = Path(__file__).resolve().parents[1]
pack_root = repo / "datapack"
pack = json.loads((pack_root / "pack.mcmeta").read_text(encoding="utf-8"))["pack"]
require(pack["min_format"] == 121 and pack["max_format"] == 121, "pack.mcmeta must target format 121")

json_files = sorted(pack_root.rglob("*.json"))
documents = {}
for path in json_files:
    documents[path] = json.loads(path.read_text(encoding="utf-8"))

functions = {}
for path in pack_root.glob("data/*/function/**/*.mcfunction"):
    namespace = path.relative_to(pack_root / "data").parts[0]
    function_path = path.relative_to(pack_root / "data" / namespace / "function").with_suffix("")
    functions[f"{namespace}:{function_path.as_posix()}"] = path

advancements = {}
for path in pack_root.glob("data/*/advancement/**/*.json"):
    namespace = path.relative_to(pack_root / "data").parts[0]
    advancement_path = path.relative_to(pack_root / "data" / namespace / "advancement").with_suffix("")
    advancements[f"{namespace}:{advancement_path.as_posix()}"] = path

for tag_name, function_name in (("load", "biomevisible:load"), ("tick", "biomevisible:tick")):
    tag_path = pack_root / f"data/minecraft/tags/function/{tag_name}.json"
    require(tag_path in documents, f"Missing function tag: {tag_path.relative_to(repo)}")
    require(documents[tag_path].get("values") == [function_name], f"Unexpected {tag_name} tag contents")
    require(function_name in functions, f"Function tag references missing function: {function_name}")

function_ref = re.compile(r"\bfunction\s+([a-z0-9_.-]+:[a-z0-9_./-]+)")
advancement_ref = re.compile(r"\badvancement grant @s only ([a-z0-9_.-]+:[a-z0-9_./-]+)")
for path in functions.values():
    content = path.read_text(encoding="utf-8").replace("$(biome)", "badlands")
    for line_number, line in enumerate(content.splitlines(), start=1):
        require("$(" not in line or line.startswith("$"), f"Macro command needs '$': {path.relative_to(repo)}:{line_number}")
    for reference in function_ref.findall(content):
        require(reference in functions, f"{path.relative_to(repo)} references missing function {reference}")
    for reference in advancement_ref.findall(content):
        require(reference in advancements, f"{path.relative_to(repo)} references missing advancement {reference}")

detect = (pack_root / "data/biomevisible/function/player/detect.mcfunction").read_text(encoding="utf-8")
detected = Counter(re.findall(r"execute if biome ~ ~ ~ minecraft:([a-z0-9_]+)", detect))
require(set(detected) == set(biomes), "Biome detection does not cover the official registry exactly")
require(all(detected[biome] == 2 for biome in biomes), "Each biome must set its macro and enqueue once")
markers = Counter(re.findall(r"advancements=\{biomevisible:biome/([a-z0-9_]+)=true\}", detect))
require(set(markers) == set(biomes) and all(markers[biome] == 2 for biome in biomes), "Detection must use each player's hidden advancement marker")
require(".seen." not in detect, "Advancement markers are the sole discovery history")

discover = (pack_root / "data/biomevisible/function/player/discover.mcfunction").read_text(encoding="utf-8")
require('queue append value {key:"biome.minecraft.$(biome)"}' in discover, "Queue entries must be translation-key compounds")
require("advancement grant @s only biomevisible:biome/$(biome)" in discover, "Discovery must grant its marker")
require("matches 1" in discover, "Advancement grant must follow a successful append")
require(discover.index("queue append") < discover.index("advancement grant"), "Marker must be granted after enqueue")

for biome in biomes:
    advancement_id = f"biomevisible:biome/{biome}"
    require(advancement_id in advancements, f"Missing marker advancement for {biome}")
    marker = json.loads(advancements[advancement_id].read_text(encoding="utf-8"))
    require(marker.get("criteria") == {"discovered": {"trigger": "minecraft:impossible"}}, f"Invalid marker advancement: {biome}")
    require("display" not in marker and "rewards" not in marker, f"Marker must have no display or rewards: {biome}")

require(len(advancements) == len(biomes), "Unexpected extra advancement marker")
send_title = (pack_root / "data/biomevisible/function/player/send_title.mcfunction").read_text(encoding="utf-8")
require('"translate":"$(title_key)"' in send_title and '"color":"white"' in send_title, "Title must use a white client-side translation")
require("return run title @s title" in send_title, "Title function must return the title command's exact result")
dispatch = (pack_root / "data/biomevisible/function/player/dispatch.mcfunction").read_text(encoding="utf-8")
require("title @s times 20 60 20" in dispatch, "Title timing must be 20/60/20 ticks")
require(
    dispatch.index("send_title") < dispatch.index("data remove storage") < dispatch.index("cooldown set value 100"),
    "Dispatch must send, pop, then start cooldown",
)

print(f"OK: format 121; JSON, function references, 67 biome checks, markers and translations verified from {args.client_jar}")
