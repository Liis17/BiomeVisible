scoreboard players set @s bv.cd 0
scoreboard players set @s bv.ok 0
$execute unless data storage biomevisible:state players."$(key)" run data modify storage biomevisible:state players."$(key)" set value {queue:[],cooldown:0}
execute if dimension minecraft:the_nether run function biomevisible:player/detect/nether
execute if dimension minecraft:the_end run function biomevisible:player/detect/end
execute unless dimension minecraft:the_nether unless dimension minecraft:the_end run function biomevisible:player/detect/overworld
$execute store result score @s bv.cd run data get storage biomevisible:state players."$(key)".cooldown 1
execute if score @s bv.cd matches 1.. run scoreboard players remove @s bv.cd 1
$execute store result storage biomevisible:state players."$(key)".cooldown int 1 run scoreboard players get @s bv.cd
$execute if score @s bv.cd matches 0 if data storage biomevisible:state players."$(key)".queue[0] run function biomevisible:player/dispatch with storage biomevisible:macro
