#!/usr/bin/env python3
"""Check BiomeVisible's data-pack files against an official 26.3 client jar."""

from __future__ import annotations

import argparse
import json
import re
import struct
import zipfile
from collections import Counter
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


parser = argparse.ArgumentParser()
parser.add_argument("client_jar", type=Path, help="Official Minecraft 26.3 client.jar")
parser.add_argument("--ru-lang", type=Path, help="Official ru_ru.json downloaded from the 26.3 client assets")
args = parser.parse_args()

with zipfile.ZipFile(args.client_jar) as client:
    version = json.loads(client.read("version.json"))
    require(version["id"] == "26.3", "Expected the Minecraft 26.3 client jar")
    require(version["pack_version"]["data_major"] == 121, "Expected data format 121")
    require(
        (version["pack_version"]["resource_major"], version["pack_version"]["resource_minor"]) == (97, 1),
        "Expected resource format 97.1",
    )

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
    vanilla_font_providers = json.loads(
        client.read("assets/minecraft/font/include/default.json")
    )["providers"]

repo = Path(__file__).resolve().parents[1]
pack_root = repo / "datapack"
resource_root = repo / "resourcepack"
data_pack = json.loads((pack_root / "pack.mcmeta").read_text(encoding="utf-8"))["pack"]
require(
    data_pack["min_format"] == 121 and data_pack["max_format"] == 121,
    "datapack/pack.mcmeta must target format 121",
)
resource_pack = json.loads((resource_root / "pack.mcmeta").read_text(encoding="utf-8"))["pack"]
require(
    resource_pack["min_format"] == [97, 1] and resource_pack["max_format"] == [97, 1],
    "resourcepack/pack.mcmeta must target format 97.1",
)

if args.ru_lang is None:
    ru_translations = None
else:
    ru_translations = json.loads(args.ru_lang.read_text(encoding="utf-8"))
    missing_ru_translations = [
        biome for biome in biomes if f"biome.minecraft.{biome}" not in ru_translations
    ]
    require(not missing_ru_translations, f"Missing Russian biome translations: {missing_ru_translations}")

json_files = sorted(pack_root.rglob("*.json"))
documents = {}
for path in json_files:
    documents[path] = json.loads(path.read_text(encoding="utf-8"))

resource_json_files = sorted(resource_root.rglob("*.json"))
resource_documents = {}
for path in resource_json_files:
    resource_documents[path] = json.loads(path.read_text(encoding="utf-8"))

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
    content = path.read_text(encoding="utf-8")
    for line_number, line in enumerate(content.splitlines(), start=1):
        location = f"{path.relative_to(repo)}:{line_number}"
        has_macro_variable = re.search(r"\$\([^()]+\)", line) is not None
        require(not line.startswith("$") or has_macro_variable, f"Macro prefix needs a variable: {location}")
        require("$(" not in line or line.startswith("$"), f"Macro variable needs '$' prefix: {location}")
    resolved_content = content.replace("$(biome)", "badlands")
    for reference in function_ref.findall(resolved_content):
        require(reference in functions, f"{path.relative_to(repo)} references missing function {reference}")
    for reference in advancement_ref.findall(resolved_content):
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
discover_lines = discover.splitlines()
append_line = next((i for i, line in enumerate(discover_lines) if "queue append" in line), -1)
grant_line = next((i for i, line in enumerate(discover_lines) if "advancement grant @s only biomevisible:biome/$(biome)" in line), -1)
reward_line = next((i for i, line in enumerate(discover_lines) if "function biomevisible:player/reward_experience" in line), -1)
require(append_line >= 0 and grant_line > append_line, "Discovery must grant its marker after enqueue")
require("store success score @s bv.ok" in discover_lines[append_line], "Queue append success must be captured")
require(
    "store success score @s bv.ok" in discover_lines[grant_line]
    and "if score @s bv.ok matches 1" in discover_lines[grant_line],
    "Marker grant must run only after a successful enqueue and capture its own success",
)
require(
    reward_line > grant_line
    and "if score @s bv.ok matches 1" in discover_lines[reward_line],
    "Experience must be awarded only after a successful new marker grant",
)

reward_function = functions.get("biomevisible:player/reward_experience")
require(reward_function is not None, "Missing player/reward_experience.mcfunction")
reward_content = reward_function.read_text(encoding="utf-8")
reward_commands = [line for line in reward_content.splitlines() if line and not line.startswith("#")]
require(reward_commands == ["experience add @s 5 points"], "New discovery reward must be exactly 5 experience points")
reward_references = [
    name
    for name, path in functions.items()
    if "function biomevisible:player/reward_experience" in path.read_text(encoding="utf-8")
]
require(reward_references == ["biomevisible:player/discover"], "Experience may only be called from new discovery")

for biome in biomes:
    advancement_id = f"biomevisible:biome/{biome}"
    require(advancement_id in advancements, f"Missing marker advancement for {biome}")
    marker = json.loads(advancements[advancement_id].read_text(encoding="utf-8"))
    require(marker.get("criteria") == {"discovered": {"trigger": "minecraft:impossible"}}, f"Invalid marker advancement: {biome}")
    require("display" not in marker and "rewards" not in marker, f"Marker must have no display or rewards: {biome}")

require(len(advancements) == len(biomes), "Unexpected extra advancement marker")
large_font_path = resource_root / "assets/biomevisible/font/biome_large.json"
header_font_path = resource_root / "assets/biomevisible/font/header.json"
large_font = resource_documents.get(large_font_path, {}).get("providers", [])
require(large_font and large_font[0] == {"type": "space", "advances": {" ": 24}}, "Large font must give spaces advance 24 before bitmap providers")
vanilla_bitmap_providers = {
    provider["file"]: provider
    for provider in vanilla_font_providers
    if provider.get("file") in {
        "minecraft:font/ascii.png",
        "minecraft:font/nonlatin_european.png",
        "minecraft:font/accented.png",
    }
}
large_bitmap_providers = [provider for provider in large_font if provider.get("type") == "bitmap"]
require(
    {provider.get("file") for provider in large_bitmap_providers} == set(vanilla_bitmap_providers)
    and len(large_bitmap_providers) == len(vanilla_bitmap_providers),
    "Large font must define the vanilla ascii, nonlatin_european and accented bitmaps exactly once",
)
large_font_chars = set(" ")
for provider in large_bitmap_providers:
    source = vanilla_bitmap_providers[provider["file"]]
    vanilla_height = source.get("height", 8)
    require(
        provider.get("chars") == source["chars"]
        and provider.get("height") == vanilla_height * 6
        and provider.get("ascent") == source["ascent"] * 6 - 52,
        f"Large font must copy and scale vanilla provider {provider['file']}",
    )
    large_font_chars.update(char for row in provider["chars"] for char in row if char != "\0")
accented_chars = {
    char
    for provider in large_bitmap_providers
    if provider["file"] == "minecraft:font/accented.png"
    for row in provider["chars"]
    for char in row
    if char != "\0"
}
require(set("йё") <= accented_chars, "Accented font provider must retain Russian й and ё")

header_providers = resource_documents.get(header_font_path, {}).get("providers", [])
require(
    len(header_providers) == 2
    and header_providers[0].get("type") == "bitmap"
    and header_providers[0].get("file") == "biomevisible:font/pin.png"
    and header_providers[0].get("chars") == ["📍"]
    and header_providers[0].get("height") == 8
    and header_providers[0].get("ascent") == 7
    and header_providers[1] == {"type": "reference", "id": "minecraft:default"},
    "Header font must put the native-size pin before the vanilla default font",
)
pin_path = resource_root / "assets/biomevisible/textures/font/pin.png"
pin_png = pin_path.read_bytes()
require(pin_png[:8] == b"\x89PNG\r\n\x1a\n", "Header pin must be a PNG")
require(struct.unpack(">II", pin_png[16:24]) == (8, 8), "Header pin PNG must be 8×8 pixels")

if ru_translations is None:
    print("NOTE: Russian translation coverage was not checked; pass --ru-lang <ru_ru.json> for the full check.")
else:
    language_texts = [
        translations[f"biome.minecraft.{biome}"]
        for biome in biomes
    ] + [
        ru_translations[f"biome.minecraft.{biome}"]
        for biome in biomes
    ]
    required_font_chars = set("".join(language_texts))
    missing_font_chars = sorted(required_font_chars - large_font_chars)
    require(not missing_font_chars, f"Large font misses localized biome characters: {missing_font_chars}")

send_title = (pack_root / "data/biomevisible/function/player/send_title.mcfunction").read_text(encoding="utf-8")
send_lines = send_title.splitlines()
subtitle_index = next((i for i, line in enumerate(send_lines) if "title @s subtitle " in line), -1)
header_index = next((i for i, line in enumerate(send_lines) if "title @s title " in line), -1)
require(subtitle_index >= 0 and header_index > subtitle_index, "Subtitle must be sent before the header title trigger")
require(
    "store success score @s bv.ok run title @s subtitle " in send_lines[subtitle_index]
    and any("unless score @s bv.ok matches 1 run return 0" in line for line in send_lines[subtitle_index + 1 : header_index]),
    "Title trigger must be skipped when subtitle sending fails",
)
require("return run title @s title " in send_lines[header_index], "Title function must return header command success")
subtitle_component = json.loads(send_lines[subtitle_index].split("title @s subtitle ", 1)[1])
header_component = json.loads(send_lines[header_index].split("title @s title ", 1)[1])
require(
    subtitle_component.get("translate") == "$(title_key)"
    and subtitle_component.get("font") == "biomevisible:biome_large"
    and subtitle_component.get("color") == "white",
    "Subtitle must use the queued client-side translation in the large white font",
)
require(
    header_component.get("text") == "открыт новый биом 📍"
    and header_component.get("font") == "biomevisible:header"
    and header_component.get("color") == "white",
    "Header must use the exact white text and dedicated pin font",
)
dispatch = (pack_root / "data/biomevisible/function/player/dispatch.mcfunction").read_text(encoding="utf-8")
require("title @s times 20 60 20" in dispatch, "Title timing must be 20/60/20 ticks")
require("execute store success score @s bv.ok run function biomevisible:player/send_title" in dispatch, "Dispatch must capture success of both title sends")
require(
    dispatch.index("send_title") < dispatch.index("data remove storage") < dispatch.index("cooldown set value 100"),
    "Dispatch must send, pop, then start cooldown",
)

translation_status = "en_us + ru_ru" if ru_translations is not None else "en_us"
print(f"OK: data format 121, resource format 97.1; JSON, function references, 67 biome checks, markers, fonts and {translation_status} verified from {args.client_jar}")
