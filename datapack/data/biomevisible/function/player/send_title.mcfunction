execute store success score @s bv.ok run title @s subtitle {"text":""}
execute unless score @s bv.ok matches 1 run return fail
$return run title @s title {"translate":"biomevisible.title.$(title_key)","color":"#fffffe","shadow_color":-12632258,"font":"biomevisible:title"}
