execute store success score @s bv.ok run title @s subtitle {"text":""}
execute unless score @s bv.ok matches 1 run return fail
$execute if data storage biomevisible:macro{dim:"nether"} run return run title @s title {"translate":"biomevisible.title.$(title_key)","color":"#ff7a5c","shadow_color":-12969454,"font":"biomevisible:title"}
$execute if data storage biomevisible:macro{dim:"end"} run return run title @s title {"translate":"biomevisible.title.$(title_key)","color":"#c4b5fd","shadow_color":-14804178,"font":"biomevisible:title"}
$return run title @s title {"translate":"biomevisible.title.$(title_key)","color":"#fffffe","shadow_color":-12632258,"font":"biomevisible:title"}
