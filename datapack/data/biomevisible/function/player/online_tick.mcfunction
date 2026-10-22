scoreboard players set @s bv.cd 0
scoreboard players set @s bv.ok 0
$execute unless data storage biomevisible:state players."$(key)" run data modify storage biomevisible:state players."$(key)" set value {queue:[],cooldown:0}
# Позиция и измерение читаются с округлением вниз (scale 1), поэтому один блок — одно значение.
execute store result score @s bv.x run data get entity @s Pos[0] 1
execute store result score @s bv.y run data get entity @s Pos[1] 1
execute store result score @s bv.z run data get entity @s Pos[2] 1
scoreboard players set @s bv.dim 0
execute if dimension minecraft:the_nether run scoreboard players set @s bv.dim 1
execute if dimension minecraft:the_end run scoreboard players set @s bv.dim 2
scoreboard players set @s bv.mv 0
execute unless score @s bv.x = @s bv.lx run scoreboard players add @s bv.mv 1
execute unless score @s bv.y = @s bv.ly run scoreboard players add @s bv.mv 1
execute unless score @s bv.z = @s bv.lz run scoreboard players add @s bv.mv 1
execute unless score @s bv.dim = @s bv.ldim run scoreboard players add @s bv.mv 1
execute if score @s bv.mv matches 1.. run function biomevisible:player/detect_dimension
scoreboard players operation @s bv.lx = @s bv.x
scoreboard players operation @s bv.ly = @s bv.y
scoreboard players operation @s bv.lz = @s bv.z
scoreboard players operation @s bv.ldim = @s bv.dim
$execute store result score @s bv.cd run data get storage biomevisible:state players."$(key)".cooldown 1
execute if score @s bv.cd matches 1.. run scoreboard players remove @s bv.cd 1
$execute store result storage biomevisible:state players."$(key)".cooldown int 1 run scoreboard players get @s bv.cd
$execute if score @s bv.cd matches 0 if data storage biomevisible:state players."$(key)".queue[0] run function biomevisible:player/dispatch with storage biomevisible:macro