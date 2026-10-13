scoreboard players add #poll bv.poll 1
execute if score #poll bv.poll matches 10.. run scoreboard players set #poll bv.poll 0
execute if score #poll bv.poll matches 0 as @a at @s run function biomevisible:player/tick
