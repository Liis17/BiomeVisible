$execute unless data storage biomevisible:state players."$(key)".queue[0] run return 0
$data modify storage biomevisible:macro title_key set from storage biomevisible:state players."$(key)".queue[0].key
title @s times 20 60 20
scoreboard players set @s bv.ok 0
execute store success score @s bv.ok run function biomevisible:player/send_title with storage biomevisible:macro
$execute if score @s bv.ok matches 1 run data remove storage biomevisible:state players."$(key)".queue[0]
# cooldown считается опросами по 10 тиков: 10 опросов = 100 тиков
$execute if score @s bv.ok matches 1 run data modify storage biomevisible:state players."$(key)".cooldown set value 10
