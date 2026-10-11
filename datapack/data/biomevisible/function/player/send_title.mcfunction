$execute store success score @s bv.ok run title @s subtitle {"translate":"$(title_key)","color":"white","font":"biomevisible:biome_large"}
execute unless score @s bv.ok matches 1 run return fail
return run title @s title {"text":"открыт новый биом 📍","color":"white","font":"biomevisible:header"}
