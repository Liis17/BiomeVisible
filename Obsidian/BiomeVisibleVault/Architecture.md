# Architecture

Parent: [[Index]]

## Назначение и границы

Датапак в `datapack/` показывает игроку локализованный title при первом обнаружении каждого ванильного биома Minecraft Java Edition 26.3. Проверка идёт каждый серверный тик в позиции ног игрока; охвачены все 67 биомов, включая биомы Нижнего мира, Края и `the_void`. История начинается при установке: посещения до неё не импортируются. Сторонние биомы, звуки, subtitle, ресурс-пак, мод и API сброса не входят в контракт.

## Стек и версия

| Технология | Роль | Источник |
|------------|------|----------|
| Minecraft Java Edition 26.3 | Среда исполнения | Официальный `client.jar`, `version.json` |
| Data pack format 121 | Формат `datapack/pack.mcmeta` | `version.json`: `data_major: 121`, `data_minor: 0` |
| Minecraft functions, tags, advancements, storage | Выполнение и сохранение состояния | `datapack/data/` |
| Python 3, стандартная библиотека | Статическая проверка | `tools/check_datapack.py` |

В `pack.mcmeta` установлены `min_format` и `max_format` равные 121. Java 26.3 использует Java 25.

## Структура

```text
datapack/pack.mcmeta
datapack/data/minecraft/tags/function/load.json
datapack/data/minecraft/tags/function/tick.json
datapack/data/biomevisible/function/load.mcfunction
datapack/data/biomevisible/function/tick.mcfunction
datapack/data/biomevisible/function/player/*.mcfunction
datapack/data/biomevisible/advancement/biome/<biome>.json
tools/check_datapack.py
README.md
```

Папка `datapack/` — корень датапака. Для установки её содержимое копируют в папку мира как `datapacks/biomevisible/`.

## Поток выполнения

`minecraft:load` вызывает `biomevisible:load`, который один раз создаёт scratch scoreboard objectives `bv.cd` и `bv.ok`. `minecraft:tick` вызывает `biomevisible:tick` и обрабатывает всех онлайн-игроков через `execute as @a at @s`.

`player/tick` читает четыре int из `@s.UUID`, помещает их во временное хранилище `biomevisible:macro` и формирует ключ `<uuid0>_<uuid1>_<uuid2>_<uuid3>`. В `biomevisible:state.players."<key>"` хранится персональная запись:

```snbt
{queue:[],cooldown:0}
```

Quoted NBT path сохраняет знаки отрицательных UUID int без преобразования в имя игрока. `biomevisible:macro` — общий scratch только для последовательно обрабатываемого онлайн-игрока; UUID, id текущего биома и ключ title перезаписываются при следующем вызове.

`player/detect` проверяет все 67 `minecraft:<biome>` через `execute if biome ~ ~ ~`. Уже открытые биомы определяются по персональному advancement `biomevisible:biome/<biome>`. Каждый маркер содержит только критерий `minecraft:impossible`, без display и rewards. При новом биоме `player/discover` сначала обеспечивает очередь `[]`, добавляет compound `{key:"biome.minecraft.<biome>"}` и только при успешном append выдаёт marker advancement. Ключ использует ванильную локализацию клиента.

Каждый онлайн-тик уменьшает cooldown, если он положительный. При нуле и непустой очереди `player/dispatch` задаёт title timing `20/60/20`, получает переводной ключ головы очереди и вызывает `player/send_title`. Эта функция возвращает результат команды `title`. Только при успехе очередь извлекает голову и cooldown становится равным 100; так между отправками проходит 100 онлайн-тиков. Обрабатывается не более одного элемента за тик. Offline-игрок не попадает в `@a`, поэтому его очередь и таймер ждут следующего входа.

## Сохранение и ограничения

- Discovery history — advancement-профиль игрока; очередь и cooldown — server storage с ключом из четырёх UUID int. Они не зависят от имени игрока.
- История, очередь и cooldown сохраняются между смертью, выходом, `/reload` и перезапуском мира. Уже отправленный title не возвращается в очередь.
- Первый обнаруженный биом не пропускается. Для игрока без записи очередь и cooldown создаются при первом тике.
- В title применяется `color:"white"`, translation key из `biome.minecraft.<id>` и стандартное центрированное отображение title Minecraft.
- Minecraft использует общий title-слот: другой источник title может заменить сообщение BiomeVisible.
- Нет поддержки сторонних биомов, звуков, subtitle, ресурспака, мода или пользовательского сброса истории.

## Проверка

`python3 tools/check_datapack.py <official-client-26.3.jar>` проверяет JSON, ссылки на функции и маркеры, соответствие всем 67 биомам из jar, наличие их `en_us` ключей и формат 121. Языковое отображение, макросы в запущенном сервере и multiplayer-поведение проверяются отдельным runtime-прогоном с игрой.
