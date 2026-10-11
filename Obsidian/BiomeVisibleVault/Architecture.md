# Architecture

Parent: [[Index]]

## Назначение и границы

Датапак в `datapack/` и ресурс-пак в `resourcepack/` показывают игроку локализованное крупное название при первом обнаружении каждого ванильного биома Minecraft Java Edition 26.3. Проверка идёт каждый серверный тик в позиции ног игрока; охвачены все 67 биомов, включая биомы Нижнего мира, Края и `the_void`. История начинается при установке: посещения до неё не импортируются. Сторонние биомы, звуки, мод и API сброса не входят в контракт.

## Стек и версия

| Технология | Роль | Источник |
|------------|------|----------|
| Minecraft Java Edition 26.3 | Среда исполнения | Официальный `client.jar`, `version.json` |
| Data pack format 121 | Формат `datapack/pack.mcmeta` | `version.json`: `data_major: 121`, `data_minor: 0` |
| Resource pack format 97.1 | Формат `resourcepack/pack.mcmeta` | `version.json`: `resource_major: 97`, `resource_minor: 1` |
| Minecraft functions, tags, advancements, storage | Выполнение и сохранение состояния | `datapack/data/` |
| Minecraft fonts and bitmap providers | Заголовок и крупное название биома | `resourcepack/assets/biomevisible/font/` |
| Python 3, стандартная библиотека | Статическая проверка | `tools/check_datapack.py` |

В `pack.mcmeta` установлены `min_format` и `max_format` равные 121. Java 26.3 использует Java 25.

## Структура

```text
datapack/pack.mcmeta
datapack/pack.png                         # иконка датапака
datapack/data/minecraft/tags/function/load.json
datapack/data/minecraft/tags/function/tick.json
datapack/data/biomevisible/function/load.mcfunction
datapack/data/biomevisible/function/tick.mcfunction
datapack/data/biomevisible/function/player/*.mcfunction # включая reward_experience
datapack/data/biomevisible/advancement/biome/<biome>.json
resourcepack/pack.mcmeta
resourcepack/pack.png                      # та же иконка, что у датапака
resourcepack/assets/biomevisible/lang/{en_us,ru_ru}.json # описания обоих паков
resourcepack/assets/biomevisible/font/biome_large.json
resourcepack/assets/biomevisible/font/header.json
resourcepack/assets/biomevisible/textures/font/pin.png
tools/check_datapack.py
```

Папки `datapack/` и `resourcepack/` — корни соответствующих пакетов. Содержимое `datapack/` копируют в папку мира как `datapacks/biomevisible/`; `resourcepack/` устанавливают в клиентскую папку `resourcepacks/` и включают в настройках клиента.

## Поток выполнения

`minecraft:load` вызывает `biomevisible:load`, который один раз создаёт scratch scoreboard objectives `bv.cd` и `bv.ok`. `minecraft:tick` вызывает `biomevisible:tick` и обрабатывает всех онлайн-игроков через `execute as @a at @s`.

`player/tick` читает четыре int из `@s.UUID`, помещает их во временное хранилище `biomevisible:macro` и формирует ключ `<uuid0>_<uuid1>_<uuid2>_<uuid3>`. В `biomevisible:state.players."<key>"` хранится персональная запись:

```snbt
{queue:[],cooldown:0}
```

Quoted NBT path сохраняет знаки отрицательных UUID int без преобразования в имя игрока. `biomevisible:macro` — общий scratch только для последовательно обрабатываемого онлайн-игрока; UUID, id текущего биома и ключ title перезаписываются при следующем вызове.

`player/detect` проверяет все 67 `minecraft:<biome>` через `execute if biome ~ ~ ~`. Уже открытые биомы определяются по персональному advancement `biomevisible:biome/<biome>`. Каждый маркер содержит только критерий `minecraft:impossible`, без display и rewards. При новом биоме `player/discover` сначала обеспечивает очередь `[]`, добавляет compound `{key:"biome.minecraft.<biome>"}` и только при успешном append выдаёт marker advancement. Опыт выдаётся только после успешного append и успешной выдачи маркера: `player/reward_experience` добавляет ровно 5 points. Будущее изменение множителя обозначено комментарием в этой отдельной функции; сейчас множитель не применяется. Повторные открытия, отправка очереди и `/reload` награду не вызывают. Ключ использует ванильную локализацию клиента.

Каждый онлайн-тик уменьшает cooldown, если он положительный. При нуле и непустой очереди `player/dispatch` задаёт title timing `20/60/20`, получает переводной ключ головы очереди и вызывает `player/send_title`. Функция сначала отправляет локализованное название в subtitle со шрифтом `biomevisible:biome_large`, затем запускает отображение точной белой строки `открыт новый биом 📍` через title. Очередь удаляет элемент и ставит cooldown только при успехе обеих команд. Так между отправками проходит 100 онлайн-тиков. Обрабатывается не более одного элемента за тик. Offline-игрок не попадает в `@a`, поэтому его очередь и таймер ждут следующего входа.

`resourcepack/assets/biomevisible/font/biome_large.json` ставит space provider с advance 15 перед bitmap providers для ванильных `ascii.png`, `nonlatin_european.png` и `accented.png`. Символьные таблицы копируются из клиентского `assets/minecraft/font/include/default.json`; bitmap height равен `vanilla height × 15/4`, ascent — `round(vanilla ascent × 15/4) − 25`. При масштабе subtitle 2 это даёт буквы примерно в 1,875 раза крупнее прежнего title и поднимает название ближе к заголовку; локализованное название не переносится и может выходить за края экрана. `header.json` подменяет только символ U+1F4CD своим bitmap 8×8 и затем ссылается на `minecraft:default`, не меняя глобальный ванильный шрифт.

## Сохранение и ограничения

- Discovery history — advancement-профиль игрока; очередь и cooldown — server storage с ключом из четырёх UUID int. Они не зависят от имени игрока.
- История, очередь и cooldown сохраняются между смертью, выходом, `/reload` и перезапуском мира. Уже отправленный title не возвращается в очередь.
- Первый обнаруженный биом не пропускается. Для игрока без записи очередь и cooldown создаются при первом тике.
- Header использует стандартный title-размер и белый текст; название биома клиент переводит из ключа `biome.minecraft.<id>` на языке клиента.
- Для корректного отображения сообщения клиент должен включить BiomeVisible resource pack; шрифты проверены на все 67 ванильных en_us и ru_ru названий.
- Minecraft использует общий title-слот: другой источник title может заменить сообщение BiomeVisible.
- Нет поддержки сторонних биомов, звуков, мода или пользовательского сброса истории.

## Проверка

`python3 tools/check_datapack.py <official-client-26.3.jar> --ru-lang <official-ru_ru.json>` проверяет JSON, ссылки на функции и маркеры, соответствие всем 67 биомам из jar, выдачу опыта, обе команды сообщения, форматы 121 и 97.1, а также покрытие en_us/ru_ru названий шрифтами. Без `--ru-lang` скрипт явно сообщает о пропуске русской проверки. Языковое отображение, макросы в запущенном сервере и multiplayer-поведение проверяются отдельным runtime-прогоном с игрой.

## Метаданные пакетов

Оба `pack.mcmeta` содержат одинаковую версию проекта `MAJOR.MINOR.PATCH` в верхнеуровневом поле `version`; это метаданные проекта для сборки, не формат совместимости Minecraft. Версия также передаётся в `pack.description.with`. При изменении любого пакета повышаются обе версии согласно `AGENTS.md`.

`pack.description` — переводной текстовый компонент с английским `fallback`. Ключи обоих описаний определены в `resourcepack/assets/biomevisible/lang/en_us.json` и `ru_ru.json`; русский перевод доступен при загрузке ресурс-пака. Без перевода отображается английское описание. Оба пака используют одинаковый `pack.png`.

## Сборка и релизы

`.github/workflows/release.yml` запускается при push в `master`, затрагивающем любой пак, сборщик или сам workflow, а также вручную на `master`. Использует `contents: write`, полную историю Git и последовательную публикацию через concurrency group.

`tools/build_release.py` сравнивает папки с тегом последнего опубликованного стабильного GitHub Release. Для первого релиза собирает оба пака и включает всю историю коммитов. При отсутствии изменений паков релиз пропускается. Сборщик проверяет одинаковые версии `MAJOR.MINOR.PATCH`, отображаемые версии и повышение обеих версий относительно прошлого релиза. Изменение только версии тоже считается изменением пакета; при обычном синхронном повышении собираются оба ZIP.

Архивы `BiomeVisible-datapack-X.Y.Z.zip` и `BiomeVisible-resourcepack-X.Y.Z.zip` содержат отслеживаемые Git файлы соответствующей папки, с `pack.mcmeta` в корне ZIP. Посторонние локальные файлы не включаются. Релиз имеет тег `vX.Y.Z`, заголовок `BiomeVisible vX.Y.Z` и список всех коммитов после тега прошлого релиза. Повторный запуск на уже опубликованном состоянии не создаёт новый релиз. Проверка сборки: `python3 tools/test_build_release.py`.
