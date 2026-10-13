$execute unless data storage biomevisible:state players."$(key)".queue run data modify storage biomevisible:state players."$(key)".queue set value []
$execute store success score @s bv.ok run data modify storage biomevisible:state players."$(key)".queue append value {key:"biome.minecraft.$(biome)"}
$execute store success score @s bv.ok if score @s bv.ok matches 1 run advancement grant @s only biomevisible:biome/$(biome)
# Future: multiply the base reward of 5 points by a multiplier if the reward policy changes.
execute if score @s bv.ok matches 1 run experience add @s 5 points
