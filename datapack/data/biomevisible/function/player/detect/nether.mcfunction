# Nether biomes: called from player/online_tick only in minecraft:the_nether.
data remove storage biomevisible:macro biome
execute if biome ~ ~ ~ minecraft:basalt_deltas unless entity @s[advancements={biomevisible:biome/basalt_deltas=true}] run data modify storage biomevisible:macro biome set value "basalt_deltas"
execute if biome ~ ~ ~ minecraft:crimson_forest unless entity @s[advancements={biomevisible:biome/crimson_forest=true}] run data modify storage biomevisible:macro biome set value "crimson_forest"
execute if biome ~ ~ ~ minecraft:nether_wastes unless entity @s[advancements={biomevisible:biome/nether_wastes=true}] run data modify storage biomevisible:macro biome set value "nether_wastes"
execute if biome ~ ~ ~ minecraft:soul_sand_valley unless entity @s[advancements={biomevisible:biome/soul_sand_valley=true}] run data modify storage biomevisible:macro biome set value "soul_sand_valley"
execute if biome ~ ~ ~ minecraft:warped_forest unless entity @s[advancements={biomevisible:biome/warped_forest=true}] run data modify storage biomevisible:macro biome set value "warped_forest"
execute if data storage biomevisible:macro biome run function biomevisible:player/discover with storage biomevisible:macro
