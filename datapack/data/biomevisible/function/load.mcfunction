execute unless data storage biomevisible:state initialized run scoreboard objectives add bv.cd dummy
execute unless data storage biomevisible:state initialized run scoreboard objectives add bv.ok dummy
execute unless data storage biomevisible:state initialized run data modify storage biomevisible:state initialized set value 1b
execute unless data storage biomevisible:state poll_initialized run scoreboard objectives add bv.poll dummy
execute unless data storage biomevisible:state poll_initialized run data modify storage biomevisible:state poll_initialized set value 1b
execute unless data storage biomevisible:state cache_initialized run scoreboard objectives add bv.x dummy
execute unless data storage biomevisible:state cache_initialized run scoreboard objectives add bv.y dummy
execute unless data storage biomevisible:state cache_initialized run scoreboard objectives add bv.z dummy
execute unless data storage biomevisible:state cache_initialized run scoreboard objectives add bv.lx dummy
execute unless data storage biomevisible:state cache_initialized run scoreboard objectives add bv.ly dummy
execute unless data storage biomevisible:state cache_initialized run scoreboard objectives add bv.lz dummy
execute unless data storage biomevisible:state cache_initialized run scoreboard objectives add bv.dim dummy
execute unless data storage biomevisible:state cache_initialized run scoreboard objectives add bv.ldim dummy
execute unless data storage biomevisible:state cache_initialized run scoreboard objectives add bv.mv dummy
execute unless data storage biomevisible:state cache_initialized run data modify storage biomevisible:state cache_initialized set value 1b