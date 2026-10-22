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
nbt_in_path = re.compile(r"storage [a-z0-9_.\-]+\{")
for path in functions.values():
    content = path.read_text(encoding="utf-8")
    for line_number, line in enumerate(content.splitlines(), start=1):
        location = f"{path.relative_to(repo)}:{line_number}"
        has_macro_variable = re.search(r"\$\([^()]+\)", line) is not None
        require(not line.startswith("$") or has_macro_variable, f"Macro prefix needs a variable: {location}")
        require("$(" not in line or line.startswith("$"), f"Macro variable needs '$' prefix: {location}")
        require(
            not nbt_in_path.search(line),
            f"NBT argument must be separated from the storage path by a space: {location}",
        )
    resolved_content = content.replace("$(biome)", "badlands")
    for reference in function_ref.findall(resolved_content):
        require(reference in functions, f"{path.relative_to(repo)} references missing function {reference}")
    for reference in advancement_ref.findall(resolved_content):
        require(reference in advancements, f"{path.relative_to(repo)} references missing advancement {reference}")

detect_root = pack_root / "data/biomevisible/function/player/detect"
detect_texts = {name: (detect_root / f"{name}.mcfunction").read_text(encoding="utf-8") for name in ("overworld", "nether", "end")}
detect = "\n".join(detect_texts.values())
detected = Counter(
    re.findall(
        r'execute if biome ~ ~ ~ minecraft:([a-z0-9_]+) unless entity @s\[advancements=\{biomevisible:biome/\1=true\}\] run data modify storage biomevisible:macro biome set value "\1"',
        detect,
    )
)
require(set(detected) == set(biomes), "Biome detection does not cover the official registry exactly")
require(all(detected[biome] == 1 for biome in biomes), "Each biome must be detected exactly once across dimensions")
for name, text in detect_texts.items():
    require("data remove storage biomevisible:macro biome" in text, f"Detect {name} must clear the stale biome first")
    require(
        text.rstrip().endswith("execute if data storage biomevisible:macro biome run function biomevisible:player/discover with storage biomevisible:macro"),
        f"Detect {name} must enqueue once after all biome checks",
    )
detect_dimension = (pack_root / "data/biomevisible/function/player/detect_dimension.mcfunction").read_text(encoding="utf-8")
require(
    "execute if dimension minecraft:the_nether run function biomevisible:player/detect/nether" in detect_dimension
    and "execute if dimension minecraft:the_end run function biomevisible:player/detect/end" in detect_dimension
    and "execute unless dimension minecraft:the_nether unless dimension minecraft:the_end run function biomevisible:player/detect/overworld" in detect_dimension,
    "Detection must dispatch by dimension",
)
online_tick = (pack_root / "data/biomevisible/function/player/online_tick.mcfunction").read_text(encoding="utf-8")
online_lines = online_tick.splitlines()
for axis in ("[0]", "[1]", "[2]"):
    require(
        f"execute store result score @s bv.{'xyz'[int(axis[1])]} run data get entity @s Pos{axis} 1" in online_lines,
        f"Online tick must read Pos{axis} with scale 1 (rounded down)",
    )
for current, last in (("x", "lx"), ("y", "ly"), ("z", "lz"), ("dim", "ldim")):
    require(
        f"execute unless score @s bv.{current} = @s bv.{last} run scoreboard players add @s bv.mv 1" in online_lines,
        f"Position cache must compare bv.{current} against bv.{last}",
    )
    require(
        f"scoreboard players operation @s bv.{last} = @s bv.{current}" in online_lines,
        f"Position cache must remember bv.{current}",
    )
require(
    "execute if score @s bv.mv matches 1.. run function biomevisible:player/detect_dimension" in online_lines,
    "Detection must run only after a position or dimension change",
)
require(
    online_lines.index("execute if score @s bv.mv matches 1.. run function biomevisible:player/detect_dimension")
    < online_lines.index("scoreboard players operation @s bv.lx = @s bv.x"),
    "Detection must run before the cache is updated",
)
require("execute if dimension minecraft:the_nether run scoreboard players set @s bv.dim 1" in online_lines, "Position cache must include the dimension")
load_function = (pack_root / "data/biomevisible/function/load.mcfunction").read_text(encoding="utf-8")
for objective in ("x", "y", "z", "lx", "ly", "lz", "dim", "ldim", "mv"):
    require(
        f"execute unless data storage biomevisible:state cache_initialized run scoreboard objectives add bv.{objective} dummy" in load_function,
        f"Position cache is missing objective bv.{objective}",
    )
markers = Counter(re.findall(r"advancements=\{biomevisible:biome/([a-z0-9_]+)=true\}", detect))
require(set(markers) == set(biomes) and all(markers[biome] == 1 for biome in biomes), "Detection must use each player's hidden advancement marker")
require(".seen." not in detect, "Advancement markers are the sole discovery history")

discover = (pack_root / "data/biomevisible/function/player/discover.mcfunction").read_text(encoding="utf-8")
require('queue append value {key:"biome.minecraft.$(biome)"}' in discover, "Queue entries must be translation-key compounds")
discover_lines = discover.splitlines()
append_line = next((i for i, line in enumerate(discover_lines) if "queue append" in line), -1)
grant_line = next((i for i, line in enumerate(discover_lines) if "advancement grant @s only biomevisible:biome/$(biome)" in line), -1)
reward_line = next((i for i, line in enumerate(discover_lines) if "experience add @s 5 points" in line), -1)
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

require(not (pack_root / "data/biomevisible/function/player/reward_experience.mcfunction").exists(), "Reward must live inside discover")
experience_lines = [line for line in discover_lines if "experience add" in line]
require(experience_lines == ["execute if score @s bv.ok matches 1 run experience add @s 5 points"], "New discovery reward must be exactly 5 experience points")
reward_references = [
    name
    for name, path in functions.items()
    if "experience add" in path.read_text(encoding="utf-8")
]
require(reward_references == ["biomevisible:player/discover"], "Experience may only be granted from new discovery")

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
title_indices = [i for i, line in enumerate(send_lines) if "title @s title " in line]
require(subtitle_index >= 0 and len(title_indices) == 3 and all(i > subtitle_index for i in title_indices),
       "Subtitle must precede three dimension-specific title triggers")
require(
    "store success score @s bv.ok run title @s subtitle " in send_lines[subtitle_index]
    and any("unless score @s bv.ok matches 1 run return fail" in line for line in send_lines[subtitle_index + 1 : title_indices[0]]),
    "Title trigger must be skipped when subtitle sending fails",
)
expected_colors = [("#ff7a5c", -12969454), ("#c4b5fd", -14804178), ("#fffffe", -12632258)]
subtitle_component = json.loads(send_lines[subtitle_index].split("title @s subtitle ", 1)[1])
require(subtitle_component == {"text": ""}, "Subtitle must clear any preceding subtitle")
for idx, (exp_color, exp_shadow) in zip(title_indices, expected_colors):
    require("$return run title @s title " in send_lines[idx] or "return run title @s title " in send_lines[idx],
           "Each title trigger must return header command success")
    component = json.loads(send_lines[idx].split("title @s title ", 1)[1])
    require(
        component.get("translate") == "biomevisible.title.$(title_key)"
        and component.get("font") == "biomevisible:title"
        and component.get("color") == exp_color
        and component.get("shadow_color") == exp_shadow,
        "Title must use the localized wrapped glyph and dimension-specific shader colors",
    )
dispatch = (pack_root / "data/biomevisible/function/player/dispatch.mcfunction").read_text(encoding="utf-8")
require("title @s times 20 60 20" in dispatch, "Title timing must be 20/60/20 ticks")
require("execute store success score @s bv.ok run function biomevisible:player/send_title" in dispatch, "Dispatch must capture success of both title sends")
require(
    any(line.endswith("cooldown set value 10") for line in dispatch.splitlines()),
    "Cooldown must be 10 polls (100 ticks) after a successful title",
)
require(
    dispatch.index("send_title") < dispatch.index("data remove storage") < dispatch.index("cooldown set value 10"),
    "Dispatch must send, pop, then start cooldown",
)
tick_function = (pack_root / "data/biomevisible/function/tick.mcfunction").read_text(encoding="utf-8")
require(
    "execute if score #poll bv.poll matches 0 as @a at @s run function biomevisible:player/tick" in tick_function
    and "matches 10.." in tick_function,
    "Player checks must run once per 10 ticks",
)

print(
    f"OK: data format 121, resource format 97.1; JSON, function references, 67 biome checks, markers, "
    f"{len(TITLE_LANGUAGES)} title fonts and {' + '.join(checked_languages)} translations "
    f"verified from {args.client_jar}"
)
