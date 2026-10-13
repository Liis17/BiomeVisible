execute if dimension minecraft:the_nether run function biomevisible:player/detect/nether
execute if dimension minecraft:the_end run function biomevisible:player/detect/end
execute unless dimension minecraft:the_nether unless dimension minecraft:the_end run function biomevisible:player/detect/overworld