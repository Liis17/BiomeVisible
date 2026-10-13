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
parser.add_argument(
    "--lang-dir",
    type=Path,
    help="Directory holding the official <locale>.json files of every title language except en_us and ru_ru",
)
args = parser.parse_args()

TITLE_LANGUAGES = (
    "en_us",
    "ru_ru",
    "de_de",
    "fr_fr",
    "es_es",
    "it_it",
    "pl_pl",
    "nl_nl",
    "pt_br",
)

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
    print("NOTE: Russian source translations were not checked; pass --ru-lang <ru_ru.json>.")
    ru_translations = None
else:
    ru_translations = json.loads(args.ru_lang.read_text(encoding="utf-8"))
    missing_ru_translations = [
        biome for biome in biomes if f"biome.minecraft.{biome}" not in ru_translations
    ]
    require(not missing_ru_translations, f"Missing Russian biome translations: {missing_ru_translations}")

checked_languages = ["en_us"] + (["ru_ru"] if ru_translations is not None else [])
if args.lang_dir is None:
    print(
        "NOTE: Extra language source translations were not checked; "
        "pass --lang-dir <directory> with the official <locale>.json files."
    )
else:
    for language in TITLE_LANGUAGES[2:]:
        path = args.lang_dir / f"{language}.json"
        require(path.exists(), f"Missing official translations: {path}")
        source = json.loads(path.read_text(encoding="utf-8"))
        missing = [biome for biome in biomes if f"biome.minecraft.{biome}" not in source]
        require(not missing, f"Missing {language} biome translations: {missing}")
        checked_languages.append(language)

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
title_font_path = resource_root / "assets/biomevisible/font/title.json"
providers = resource_documents.get(title_font_path, {}).get("providers", [])
require(len(providers) == len(TITLE_LANGUAGES) + 1, "Title font must contain spacing and one atlas per language")
require(providers[0] == {"type": "space", "advances": {"\uf000": -1}}, "Title halves must cancel the vanilla one-pixel glyph spacing")
for language_index, language in enumerate(TITLE_LANGUAGES):
    provider = providers[language_index + 1]
    require(provider.get("type") == "bitmap", "Title provider must use bitmap glyphs")
    require(provider.get("file") == f"biomevisible:font/titles_{language}.png", "Wrong title atlas")
    require(provider.get("ascent") == 7 and provider.get("height") == 68, "Title geometry must match the shader")
    rows = provider.get("chars", [])
    require(len(rows) == 17 and all(len(row) == 8 for row in rows), "Atlas must contain 8 x 17 cells")
    glyphs = "".join(rows).replace("\0", "")
    expected = "".join(chr(0xE000 + language_index * len(biomes) * 2 + i) for i in range(len(biomes) * 2))
    require(glyphs == expected, "Title glyphs must cover each biome exactly once")
    lang = resource_documents[resource_root / f"assets/biomevisible/lang/{language}.json"]
    title_keys = {key for key in lang if key.startswith("biomevisible.title.")}
    require(title_keys == {f"biomevisible.title.biome.minecraft.{biome}" for biome in biomes}, "Title translations must cover all biomes")
    for i, biome in enumerate(biomes):
        require(lang[f"biomevisible.title.biome.minecraft.{biome}"] == expected[i * 2] + "\uf000" + expected[i * 2 + 1] + "\uf000", f"Wrong {language} glyph for {biome}")
    png = (resource_root / f"assets/biomevisible/textures/font/titles_{language}.png").read_bytes()
    require(png[:8] == b"\x89PNG\r\n\x1a\n", "Title atlas must be PNG")
    require(struct.unpack(">II", png[16:24]) == (1064, 1156), "Atlas dimensions must match title geometry")
shader = (resource_root / "assets/minecraft/shaders/core/text.vsh").read_text()
require("#ifdef IS_GUI" in shader and "biomeTitle || biomeShadow" in shader, "Title positioning must only target marked GUI text")
require("ScreenSize.x * 0.7 / 266.0" in shader and "ScreenSize.y * 0.3 / 68.0" in shader, "Title must fit within the window")
require("vec2(0.0, 40.0)" in shader and "12.0 / guiPerFramebufferPixel.y" in shader, "Title must anchor 12 GUI pixels below the top")

require("floor(min(2.0 / guiPerFramebufferPixel.x" in shader and "round(pixelPosition)" in shader, "Title texels and origins must align with framebuffer pixels")
with zipfile.ZipFile(args.client_jar) as client:
    require((resource_root / "assets/minecraft/shaders/core/text.fsh").read_bytes()
            == client.read("assets/minecraft/shaders/core/text.fsh"),
            "The paired fragment shader must match the official client")

send_title = (pack_root / "data/biomevisible/function/player/send_title.mcfunction").read_text(encoding="utf-8")
send_lines = send_title.splitlines()
subtitle_index = next((i for i, line in enumerate(send_lines) if "title @s subtitle " in line), -1)
header_index = next((i for i, line in enumerate(send_lines) if "title @s title " in line), -1)
require(subtitle_index >= 0 and header_index > subtitle_index, "Subtitle must be sent before the header title trigger")
require(
    "store success score @s bv.ok run title @s subtitle " in send_lines[subtitle_index]
    and any("unless score @s bv.ok matches 1 run return fail" in line for line in send_lines[subtitle_index + 1 : header_index]),
    "Title trigger must be skipped when subtitle sending fails",
)
require("return run title @s title " in send_lines[header_index], "Title function must return header command success")
subtitle_component = json.loads(send_lines[subtitle_index].split("title @s subtitle ", 1)[1])
header_component = json.loads(send_lines[header_index].split("title @s title ", 1)[1])
require(subtitle_component == {"text": ""}, "Subtitle must clear any preceding subtitle")
require(
    header_component.get("translate") == "biomevisible.title.$(title_key)"
    and header_component.get("font") == "biomevisible:title"
    and header_component.get("color") == "#fffffe"
    and header_component.get("shadow_color") == -12632258,
    "Title must use the localized wrapped glyph and dedicated shader colors",
)
dispatch = (pack_root / "data/biomevisible/function/player/dispatch.mcfunction").read_text(encoding="utf-8")
require("title @s times 20 60 20" in dispatch, "Title timing must be 20/60/20 ticks")
require("execute store success score @s bv.ok run function biomevisible:player/send_title" in dispatch, "Dispatch must capture success of both title sends")
require(
    dispatch.index("send_title") < dispatch.index("data remove storage") < dispatch.index("cooldown set value 100"),
    "Dispatch must send, pop, then start cooldown",
)

print(
    f"OK: data format 121, resource format 97.1; JSON, function references, 67 biome checks, markers, "
    f"{len(TITLE_LANGUAGES)} title fonts and {' + '.join(checked_languages)} translations "
    f"verified from {args.client_jar}"
)
