# End biomes: called from player/online_tick only in minecraft:the_end.
data remove storage biomevisible:macro biome
execute if biome ~ ~ ~ minecraft:end_barrens unless entity @s[advancements={biomevisible:biome/end_barrens=true}] run data modify storage biomevisible:macro biome set value "end_barrens"
execute if biome ~ ~ ~ minecraft:end_highlands unless entity @s[advancements={biomevisible:biome/end_highlands=true}] run data modify storage biomevisible:macro biome set value "end_highlands"
execute if biome ~ ~ ~ minecraft:end_midlands unless entity @s[advancements={biomevisible:biome/end_midlands=true}] run data modify storage biomevisible:macro biome set value "end_midlands"
execute if biome ~ ~ ~ minecraft:small_end_islands unless entity @s[advancements={biomevisible:biome/small_end_islands=true}] run data modify storage biomevisible:macro biome set value "small_end_islands"
execute if biome ~ ~ ~ minecraft:the_end unless entity @s[advancements={biomevisible:biome/the_end=true}] run data modify storage biomevisible:macro biome set value "the_end"
execute if data storage biomevisible:macro biome run function biomevisible:player/discover with storage biomevisible:macro
