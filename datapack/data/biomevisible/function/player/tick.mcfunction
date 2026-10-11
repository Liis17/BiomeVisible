data modify storage biomevisible:macro uuid set from entity @s UUID
execute store result storage biomevisible:macro uuid0 int 1 run data get storage biomevisible:macro uuid[0]
execute store result storage biomevisible:macro uuid1 int 1 run data get storage biomevisible:macro uuid[1]
execute store result storage biomevisible:macro uuid2 int 1 run data get storage biomevisible:macro uuid[2]
execute store result storage biomevisible:macro uuid3 int 1 run data get storage biomevisible:macro uuid[3]
function biomevisible:player/keyify with storage biomevisible:macro
