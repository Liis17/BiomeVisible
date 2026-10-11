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
| Minecraft bitmap fonts и GUI text shader | Локализованный блок у верхнего края окна | `resourcepack/assets/biomevisible/font/title.json`, `resourcepack/assets/minecraft/shaders/core/text.vsh` |
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
resourcepack/assets/biomevisible/lang/{en_us,ru_ru}.json # описания паков и ключи блоков
resourcepack/assets/biomevisible/font/title.json
resourcepack/assets/biomevisible/textures/font/titles_{en_us,ru_ru}.png
resourcepack/assets/minecraft/shaders/core/text.vsh
resourcepack/assets/biomevisible/textures/font/pin.png
tools/check_datapack.py
tools/build_title_assets.py               # генератор bitmap-блоков, требует Pillow
```

Папки `datapack/` и `resourcepack/` — корни соответствующих пакетов. Содержимое `datapack/` копируют в папку мира как `datapacks/biomevisible/`; `resourcepack/` устанавливают в клиентскую папку `resourcepacks/` и включают в настройках клиента.

## Поток выполнения

`minecraft:load` вызывает `biomevisible:load`, который один раз создаёт scratch scoreboard objectives `bv.cd` и `bv.ok`. `minecraft:tick` вызывает `biomevisible:tick` и обрабатывает всех онлайн-игроков через `execute as @a at @s`.

`player/tick` читает четыре int из `@s.UUID`, помещает их во временное хранилище `biomevisible:macro` и формирует ключ `<uuid0>_<uuid1>_<uuid2>_<uuid3>`. В `biomevisible:state.players."<key>"` хранится персональная запись:

```snbt
{queue:[],cooldown:0}
```

Quoted NBT path сохраняет знаки отрицательных UUID int без преобразования в имя игрока. `biomevisible:macro` — общий scratch только для последовательно обрабатываемого онлайн-игрока; UUID, id текущего биома и ключ title перезаписываются при следующем вызове.

`player/detect` проверяет все 67 `minecraft:<biome>` через `execute if biome ~ ~ ~`. Уже открытые биомы определяются по персональному advancement `biomevisible:biome/<biome>`. Каждый маркер содержит только критерий `minecraft:impossible`, без display и rewards. При новом биоме `player/discover` сначала обеспечивает очередь `[]`, добавляет compound `{key:"biome.minecraft.<biome>"}` и только при успешном append выдаёт marker advancement. Опыт выдаётся только после успешного append и успешной выдачи маркера: `player/reward_experience` добавляет ровно 5 points. Будущее изменение множителя обозначено комментарием в этой отдельной функции; сейчас множитель не применяется. Повторные открытия, отправка очереди и `/reload` награду не вызывают. Ключ хранит идентификатор ванильного перевода; при отправке он преобразуется в ключ собственного блока ресурспака.

Каждый онлайн-тик уменьшает cooldown, если он положительный. При нуле и непустой очереди `player/dispatch` задаёт title timing `20/60/20`, получает ключ головы очереди и вызывает `player/send_title`. Функция сначала очищает subtitle, затем запускает title с ключом `biomevisible.title.$(title_key)` и шрифтом `biomevisible:title`. Очередь удаляет элемент и ставит cooldown только при успехе обеих команд. Так между отправками проходит 100 онлайн-тиков. Обрабатывается не более одного элемента за тик. Offline-игрок не попадает в `@a`, поэтому его очередь и таймер ждут следующего входа.

`tools/build_title_assets.py` читает названия и bitmap-шрифты официального клиента, а также официальный `ru_ru.json`; каждый текст названия разбивается на строки по два слова максимум. Две PNG-таблицы содержат по 67 готовых блоков: заголовок, значок и центрированные строки названия. Русский заголовок — «открыт новый биом», английский — «new biome discovered». Название рисуется в 1,5 раза крупнее заголовка. Переводные ключи `biomevisible.title.biome.minecraft.<id>` выбирают один символ private-use: английские U+E000…U+E042, русские U+E043…U+E085. Клиент загружает en_us как базовый язык, поэтому для любого языка, кроме ru_ru, весь блок остаётся английским. Ванильные ключи биомов не переопределяются; старые записи очереди сохраняют совместимость.

`font/title.json` задаёт два bitmap providers: ячейки 200×56, height 56 и ascent 7. `assets/minecraft/shaders/core/text.vsh` основан на шейдере официального клиента 26.3. В GUI он распознаёт цвет title #fffffe и заданный shadow_color #ff3f3f3e, переносит блок из ванильного центра к отступу 12 GUI-пикселей сверху и сохраняет горизонтальное центрирование. Ванильный title использует масштаб 4 и y=-10 (`Hud.extractTitle`); эти значения учитываются в преобразовании. Размер блока уменьшается при необходимости до 90% ширины и 40% высоты окна. Остальной текст проходит исходный путь шейдера. Шейдер и размеры атласов должны оставаться согласованными.

## Сохранение и ограничения

- Discovery history — advancement-профиль игрока; очередь и cooldown — server storage с ключом из четырёх UUID int. Они не зависят от имени игрока.
- История, очередь и cooldown сохраняются между смертью, выходом, `/reload` и перезапуском мира. Уже отправленный title не возвращается в очередь.
- Первый обнаруженный биом не пропускается. Для игрока без записи очередь и cooldown создаются при первом тике.
- Весь блок русский при ru_ru; для остальных языков клиента — английский. Используются официальные en_us/ru_ru названия биомов.
- Клиент должен включить BiomeVisible resource pack. Изменение расположения зависит от GUI core shader `text.vsh`; другой пак, переопределяющий этот шейдер, или модифицированный рендерер могут нарушить расположение. Другой GUI-текст с теми же служебными цветами также будет перемещён.
- Minecraft использует общий title-слот: другой источник title может заменить сообщение BiomeVisible.
- Нет поддержки сторонних биомов, звуков, мода или пользовательского сброса истории.

## Проверка

`python3 tools/check_datapack.py <official-client-26.3.jar> --ru-lang <official-ru_ru.json>` проверяет JSON, ссылки на функции и маркеры, соответствие всем 67 биомам из jar, выдачу опыта, обе команды сообщения, форматы 121 и 97.1, а также ключи переводов, bitmap-таблицы и контракт геометрии шейдера. Без `--ru-lang` скрипт явно сообщает о пропуске русской проверки. `tools/build_title_assets.py <client.jar> --ru-lang <ru_ru.json> --check` с Pillow проверяет точное соответствие PNG и JSON повторной генерации из официальных ресурсов. Для обновления ресурсов ту же команду запускают без `--check`. Языковое отображение и положение при разных размерах окна и GUI Scale требуют runtime-прогона с клиентом игры; серверная проверка подтверждает команды и макросы, но не GPU-отображение.

## Метаданные пакетов

Оба `pack.mcmeta` содержат одинаковую версию проекта `MAJOR.MINOR.PATCH` в верхнеуровневом поле `version`; это метаданные проекта для сборки, не формат совместимости Minecraft. Версия также передаётся в `pack.description.with`. При изменении любого пакета повышаются обе версии согласно `AGENTS.md`.

`pack.description` — переводной текстовый компонент с английским `fallback`. Ключи обоих описаний определены в `resourcepack/assets/biomevisible/lang/en_us.json` и `ru_ru.json`; русский перевод доступен при загрузке ресурс-пака. Без перевода отображается английское описание. Оба пака используют одинаковый `pack.png`.

## Сборка и релизы

`.github/workflows/release.yml` запускается при push в `master`, затрагивающем любой пак, сборщик или сам workflow, а также вручную на `master`. Использует `contents: write`, полную историю Git и последовательную публикацию через concurrency group.

`tools/build_release.py` сравнивает папки с тегом последнего опубликованного стабильного GitHub Release. Для первого релиза собирает оба пака и включает всю историю коммитов. При отсутствии изменений паков релиз пропускается. Сборщик проверяет одинаковые версии `MAJOR.MINOR.PATCH`, отображаемые версии и повышение обеих версий относительно прошлого релиза. Изменение только версии тоже считается изменением пакета; при обычном синхронном повышении собираются оба ZIP.

Архивы `BiomeVisible-datapack-X.Y.Z.zip` и `BiomeVisible-resourcepack-X.Y.Z.zip` содержат отслеживаемые Git файлы соответствующей папки, с `pack.mcmeta` в корне ZIP. Посторонние локальные файлы не включаются. Релиз имеет тег `vX.Y.Z`, заголовок `BiomeVisible vX.Y.Z` и список всех коммитов после тега прошлого релиза. Повторный запуск на уже опубликованном состоянии не создаёт новый релиз. Проверка сборки: `python3 tools/test_build_release.py`.
