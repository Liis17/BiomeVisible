$execute unless data storage biomevisible:state players."$(key)".queue run data modify storage biomevisible:state players."$(key)".queue set value []
scoreboard players set @s bv.ok 0
$execute store success score @s bv.ok run data modify storage biomevisible:state players."$(key)".queue append value {key:"biome.minecraft.$(biome)"}
$execute if score @s bv.ok matches 1 run advancement grant @s only biomevisible:biome/$(biome)
