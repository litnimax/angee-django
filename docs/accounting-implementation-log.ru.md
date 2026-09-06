# Журнал реализации accounting по онтологии Odoo 19

Начало: 2026-09-05. Журнал фиксирует решения, фактически выполненные изменения, проверки и открытые вопросы. План не считается выполненной реализацией.

Исходный анализ: https://gist.github.com/litnimax/7985e3bb4f7a0a829df17e424fdee800

## 001 — Границы работы

**Решение.** Odoo 19 используется как бизнес-онтология и каталог сценариев. Бухгалтерские правила остаются в `/workspace/arpee-angee/addons/arp/accounting`. Доработки общих механизмов Angee выполняются в `/home/paseo/.paseo/worktrees/1s29tjir/exotic-pony`, worktree `/workspace/angee-django`, ветка `astra/invoice-form-contract`. Перенос accounting в angee-django не требуется. Предложение обсуждать такой перенос в исходном анализе отозвано после уточнения пользователя.

**Исходные снимки:** arpee `fa5c444125595e82260d45e2e53d4c7994ed3ce5`; Angee `64f1d1750f7a9f5afbefc3ce3196fa190ee44280`; Odoo `1a13ceeaee12fe5cc50f287c31f217d4be2a2eaf`.

## 002 — Первый пакет

**План.** Сначала получить воспроизводимую сборку и baseline существующих accounting tests, затем исправить регистрацию платежей: остаток вместо total, независимость направления денег от типа контрагента, валидация платежной группы и банковских счетов. Reconciliation graph, posting guards и последующие этапы остаются в очереди исходного плана.

**Владельцы.** PaymentManager владеет регистрацией и блокировками группы; Invoice/JournalItem — задолженностью и ее остатком; Payment — типом контрагента, направлением и своей проводкой; GraphQL — авторизацией и вызовом предметной операции; React — декларацией формы. Django/PostgreSQL владеют транзакциями и constraints, Angee — существующими money/sequence/transitions. Новая зависимость не предполагается.

**Аналоги.** Существующие InvoiceManager.create_document и фабрики sales/purchase; блокировки в JournalItemManager.reconcile; общий GraphQL write backend и текущая PaymentsPage. Не вводить расчет остатков на frontend или параллельную нумерацию.

**Приемка пакета.** Счет 100 → платеж 40 → платеж по умолчанию 60; возвраты по обоим типам контрагентов; отказ на пустом/несовместимом наборе; отсутствие банковского счета не подменяется receivable; повторный/конкурентный запрос не создает непреднамеренную переплату. Проверки должны проверять проводки и остатки, а не только status.

## 003 — Проверка окружения

**Выполнено.** Проверены README, manage.py, settings.yaml, исходные модели и тесты arpee, backend guidelines и локальный skill angee-workspace в Angee. Рабочее дерево arpee чистое; в worktree Angee находится созданный ранее отчет.

**Наблюдение.** В arpee и родительских каталогах, а также в цепочке родителей целевого worktree не найден angee.yaml. В PATH не найдены angee/uv, в обоих checkout Angee отсутствует .venv/bin/python. README описывает dev stack, который в этой среде не подготовлен. Сборка и тесты пока не запускались.

**Открытый вопрос.** Пользователю отправлен запрос расположения рабочего стека либо способа подготовки нового тестового стека. Skill `.agents/skills/angee-workspace/SKILL.md`, раздел Resolve The Controlling Stack Root, требует уточнить инициализацию, если ancestor stack отсутствует. Стек не инициализирован; до ответа продолжается независимая подготовка изменений и тестовых сценариев.

**Состояние реализации.** Бизнес-код пока не изменен. Журнал создан в целевом worktree; его копия публикуется отдельным gist с доступом по ссылке. Следующие записи будут добавляться по мере решений, изменений и проверок.

## 004 — Регрессионные сценарии первого пакета

**Изменено.** В `/workspace/arpee-angee/addons/arp/accounting/tests.py` добавлен `PaymentRegistrationTests` с четырьмя методами:

- После оплаты 40 из 100 второй платеж без явно заданной суммы составляет 60; оба платежа не оставляют несопоставленный остаток.
- Четыре вида invoice/refund проверяются отдельно: направление денег, знак банковской строки, счет receivable/payable и погашение документа.
- Пустой набор дает ValidationError и не создает Payment.
- Отсутствующий банковский счет блокирует posting; сохраняются draft, пустой номер и отсутствие проводки.

**Проверки.** Python 3 `ast.parse` успешно разобрал измененный файл; обнаружены четыре новых метода. `git diff --check` прошел. Django-тесты не запускались; предполагаемые падения на старой реализации не выдаются за выполненный red-run. Тесты используют существующие фикстуры и бизнес-вызовы, не заменяют Django/ORM моками. Модели, schema и UI еще не изменены.

**Публикация.** Новый gist: https://gist.github.com/litnimax/44d67e5f0e656dbce5366693082b88dc — secret, доступ по ссылке. Проверено создание. Журнал обновляется в этом же gist; исходный аналитический gist остается отдельным документом.

**Следующее действие.** Получить расположение/способ подготовки стека, запустить baseline и регрессионные тесты, затем реализовать первый пакет. Вопрос о стеке остается открытым; отсутствие ответа не считается разрешением на инициализацию.

## 005 — Выбран и подготовлен собственный стек

Пользователь разрешил использовать `/home/paseo/.paseo/worktrees/2f3fqf9s/modest-toad`, ветка `modest-toad`, worktree arpee-angee. Angee остается в `exotic-pony` на `astra/invoice-form-contract`. Указанный пользователем colorful-bumblebee в доступной файловой системе не найден; его процессы и файлы не изменялись.

Регрессионные тесты перенесены из `/workspace/arpee-angee` в modest-toad; исходный patch проверен и снят только с прежнего checkout. Созданы project pyproject/uv.lock, локальная ссылка `.angee/framework`, список framework addon/package roots и process-only `angee.yaml`. Python 3.14.7, uv 0.12.10, Angee CLI 0.12.1, process-compose 1.122.0 и pnpm 11.1.3; libmagic из Debian размещена локально в `.angee/tools/sysroot`. База — собственная SQLite `.angee/data/db.sqlite3`. Проверены свободные порты backend 8601, web 5174 и process-compose 8091. Запуск — через `angee dev`, скрипты сервисов лежат в `.angee/`.

Сборка `angee build` прошла. Первые попытки тестирования выявили неверный import label (`accounting.tests` вместо `arp.accounting.tests`) и отсутствие первичных миграций; после штатного provision миграции созданы. Установка pnpm выполнена через Corepack; попытки получить его через Python package manager/предполагаемый GitHub asset не использованы в итоговом окружении.

## 006 — Подтверждены исходные ошибки и реализован первый пакет платежей

Исходный запуск: 21 accounting test, четыре failure и один error в новых регрессионных сценариях, один PostgreSQL-only skip. Подтверждены сумма 100 вместо остатка 60, оба направления refunds, IndexError на пустой группе, отсутствие отказа при пустом банковском счете. Существующие сценарии прошли.

В `arp.accounting` внесены:

- Invoice определяет тип контрагента и направление погашения; Payment хранит отдельный `partner_type` customer/vendor, который определяет receivable/payable независимо от направления денег.
- PaymentManager.register блокирует debt items по pk, затем перечитывает/блокирует документы; порядок item→invoice соответствует обновлению статуса при reconciliation. Сумма выводится из актуальных residuals. Нет повторного расчета через amount_total.
- Проверяются непустая группа, отсутствие дубликатов, persisted/posted документы с контрагентом, одна компания/валюта/контрагент/вид документа, правильные debt items, ненулевой остаток каждого счета, положительная конечная сумма в точности валюты и конфигурация bank/cash журнала.
- Регистрация по счетам ограничена их остатком; переплата не обрезается молча. Для аванса остается отдельный standalone Payment. Смешанные invoice/refund группы не неттируются автоматически, а получают явную ошибку.
- Удален receivable fallback вместо банковского счета и прежний `_reconcile_invoices`, дублировавший вывод счета из направления. Новая валидация принадлежит Payment, resolver остается тонким.
- В GraphQL и общей форме Payment добавлен partner_type. Подготовлены addon-owned миграции Payment и HistoricalPayment: прежним outbound соответствует vendor. Исторические суммы/проводки не меняются; старые ошибочные refunds не исправляются миграцией автоматически.

Промежуточная проверка после миграций: **83 tests accounting/sales/purchase прошли, 6 PostgreSQL-only skipped**. Работа над дополнительными отрицательными и конкурентными сценариями продолжается. Reconciliation graph и полная защита posted records остаются следующими пакетами.

## 007 — Исправления, необходимые для холодного запуска демо

Первый provision выявил None.currency при загрузке строк продаж до post-load hooks компании. Owner fix: `CompanyAccounting.round_amount` принимает явную валюту документа; sales/purchase передают валюту заказа, сохраняя company rounding mode. Это исправляет также неверное округление документа в валюте с другим количеством знаков; отсутствие валюты GL теперь дает доменную ошибку.

Следующий provision выявил, что CRM Team валидирует direct membership до materialization grants. В `angee.resources` (именно exotic-pony) исправлена потеря dependencies при разделении строк и grants: используется существующий EntryGraph, независимые grants по-прежнему следуют за rows, явная зависимость row→grant имеет приоритет. Все операции атомарны; post-load hooks видят grants. CRM-манифест объявляет зависимость Team от membership grants arp.base. Проверки членства не отключались, ресурсы не исключались.

Добавлен framework regression: grant доступен при clean зависимой строки и при post-load hook; неуспешный импорт и dry run откатывают grant/rows; повторная загрузка идемпотентна. Начальная версия теста ошибочно использовала anonymous wildcard вместо auth/user wildcard; исправлена декларация тестового subject. При запуске resource suite также выявлен отдельный сбой старого теста удаления: knowledge signal ожидает RecordBinding в bare test app. Его происхождение и общий baseline еще проверяются.

После исправления порядка **полный provision --demo прошел: 437 создано, 2 обновлено; schema: ok**. Codegen frontend прошел: 22 addons, 2 схемы. Запуск сервисов и окончательные проверки еще выполняются.

## 008 — Проверки платежей, конкуренции и миграций

Расширены отрицательные сценарии: нулевая/отрицательная/не конечная сумма, переплата, лишние знаки валюты; разные компании, контрагенты и виды документов; draft, дубликат и уже оплаченный документ; журнал продаж вместо банковского и журнал чужой компании. Добавлен тест округления по валюте документа, когда валюта компании еще не установлена.

Для тестов отдельно поднят PostgreSQL 17.5 на `127.0.0.1:55441` в `.angee/pg-test`. Docker socket недоступен; использован PostgreSQL binary package из Maven Central (`io.zonky.test`, embedded-postgres-binaries-linux-amd64 17.5.0). Это временная тестовая база, основной стек остается на SQLite. Два потока одновременно регистрируют полную оплату одного счета: ровно один платеж, второй запрос получает ValidationError, остаток нулевой. Вместе с существующей конкурентной нумерацией и сценариями sales/purchase: **89 тестов, все прошли, без skip**.

После этого добавлен migration integration test: настоящие AddField/RunPython выполняются на изолированных legacy-таблицах Payment и HistoricalPayment; inbound получает customer, outbound vendor, суммы 40.25/60.75 сохраняются, повторная применимость выключается. Factory восстанавливает исходного actor после elevated bookkeeping по контракту Angee. Финальная повторная проверка accounting на PostgreSQL: **28 тестов, все прошли**. Лог содержит ошибки dev-only change publisher при DEBUG=False в тестах; dispatch.send_robust не прерывает тесты. Это не проверка доставки production-событий.

Frontend accounting: **2 файла, 5 тестов, все прошли**. Ruff по E/F/I из конфигурации Angee проходит для измененных Python business sources и resource owner; `git diff --check` и синтаксис shell проходят.

## 009 — Полный набор Angee и разбор окружения

Полный `pytest -q`: **1816 passed, 8 failed, 5 skipped** за 959.95 с. Все восемь failure находятся в `tests/test_settings.py`: унаследованный `ANGEE_PROJECT_DIR` указывал на ARPEE и мешал тестовым временным settings.yaml. Это ошибка первоначального способа запуска тестов в данной сессии. После удаления project-specific env весь модуль повторно прошел: **62 passed**. Полный набор второй раз не запускался; результаты полного запуска и адресного повторного не подменяются утверждением об одном полностью зеленом запуске.

Изолированный resource suite ранее выявил LookupError `knowledge.RecordBinding` в `pre_delete`. На чистом detached checkout исходного Angee commit `64f1d175` этот же тест воспроизводит ту же ошибку: `test_stale_ledger_pointer_to_wrong_live_row_is_repaired`, 1 failed. В полном наборе он проходит, то есть это существующая зависимость от порядка/состояния registry тестов. В production signal ничего не меняли и тест не отключали. Новая регрессия порядка row→grant проходит, включая rollback, dry-run, hook и повторный импорт.

## 010 — Живой интерфейс и воспроизводимый запуск

`angee status --json` подтверждает running для django/web. Стек: ARPEE modest-toad, Angee exotic-pony на astra/invoice-form-contract. UI `http://127.0.0.1:5174`; backend `http://127.0.0.1:8601/graphql/console/`; process-compose 8091. В текущем демо проверен вход `admin` / `admin` (это собственная база, не пароли другого агента).

При реальной проверке Playwright обнаружен blank screen: `arp.base/web/tsconfig.json` ссылался на host web на один уровень выше нужного. Исправлен относительный путь. Host tsconfig приведен к compiler contract Angee по `allowImportingTsExtensions`. CSRF для Vite-origin настроен штатным `ANGEE_PUBLIC_ORIGIN` в скрипте стека.

Сервисы теперь запускаются через отслеживаемый `scripts/accounting-dev.sh`, `angee.yaml` ссылается на него; нет обязательной зависимости от рукописных ignored `.angee/run-*.sh`. Добавлена инструкция `docs/accounting-dev.ru.md`. Generated process-compose.yaml/run исключены из git. Python dependency lock и pnpm lock сформированы для выбранных checkout. Framework JS зависимости устанавливаются по его собственному lockfile; ARPEE подключает source packages workspace links. Большой diff pnpm-lock связан с удалением прежних внешних importer paths; это следует учитывать при review инфраструктурной части.

Браузер: успешный login, загружен список продаж с демо; `/accounting/invoices`, `/accounting/payments`, `/accounting/payments/new` открыты. На трех accounting-страницах нет page errors и HTTP>=400; Partner Type виден в списке и форме. На login остаются отдельный 403 фонового изображения из внешнего worktree и отказы console-запросов до аутентификации; accounting после входа работает. Скриншоты и browser logs находятся только в ignored `.angee/browser*`.

**Ограничения и следующий шаг.** Общий frontend typecheck не проходит: устаревшие `sidebar`, `recordPath`, контракт `MutationDialog`, различия resource routes/model slots, а также отдельные React type instances из двух node_modules; recursive typecheck framework fragments также ожидает generated gql в иной topology. Это не скрыто и не объявлено исправленным проверкой только accounting. Frontend compatibility требует отдельного пакета до общего green build. Дальнейшие accounting-пакеты — корректность полного reconciliation graph, unreconcile и усиление immutability posted records — пока не реализованы. Текущий пакет исправляет регистрацию платежа; не означает production-ready accounting и не переписывает исторические ошибочные refunds.

Завершающая проверка этого пакета: `makemigrations --check --dry-run` — No changes detected; оба `git diff --check` и Ruff измененных Python owners проходят. Временный PostgreSQL остановлен после тестов, baseline worktree удален. Основные django/web остаются running. Коммиты/merge не выполнялись: изменения оставлены в двух согласованных worktree для review.

## 011 — Доступ стека по сети

По запросу пользователя backend переведен с `127.0.0.1:8601` на `0.0.0.0:8601`; Vite явно запускается с `--host 0.0.0.0` на 5174. Изменен отслеживаемый `scripts/accounting-dev.sh`, обновлена инструкция, оба сервиса перезапущены через собственный process-compose 8091. Внутренний Vite→Django proxy сохраняет loopback. Проверены listening sockets и HTTP-доступ по сетевому IP окружения.

## 012 — Обновление из litnimax/angee-django

По запросу пользователя выполнен fetch origin и fast-forward ветки astra/invoice-form-contract с `64f1d175` до `1f2b33c8` (origin/main). Обновление затрагивает 296 файлов и включает Django-native composition и новые версии опубликованных зависимостей. Основной checkout /workspace/angee-django не переключался.

Локальный resource patch предварительно сохранен в stash `accounting resource ordering before upstream 1f2b33c8` и восстановлен поверх обновления. Конфликты двух файлов разрешены: сохранены upstream Dataset/read_groups, проверка единой БД через router и перевод номера ошибки в исходную строку; поверх них сохранен dependency order rows/grants и post-load hooks после grants. Локальный regression test сохранен с новой upstream fixture API. Stash оставлен как резервная копия. Ruff и git diff --check проходят; незавершенных git-конфликтов нет. Framework uv sync выполнен.

**Обнаруженная несовместимость запуска.** Попытка сборки текущего ARPEE на новом framework завершается ImproperlyConfigured: accounting.Invoice redeclares parent field 'created_at' from accounting.JournalEntry; use a narrow abstract child/donor with only its contributed fields. Новый composer запрещает прежнюю форму наследования child/donor с унаследованными timestamp fields. Backend после autoreload не отвечает; актуализация git завершена, совместимость работающего стека после обновления НЕ подтверждена. Требуется отдельная адаптация ARPEE к native composition; массовые изменения бизнес-моделей и миграции базы в рамках подтягивания upstream не выполнялись.

Адресный resource suite: 23 passed, 23 setup errors (Related model 'parties.Handle' cannot be resolved в upstream test registry); это не зеленая верификация совмещенного патча. Полный набор после обновления не запускался. Ранее опубликованные результаты проверок относятся к старой базе framework и не переносятся автоматически на 1f2b33c8.

## 013 — Адаптация ARPEE к native composition

Пользователь разрешил адаптацию. В ARPEE materialized Invoice и все same-row donors переведены с AngeeModel на узкие abstract Django models; Invoice сохраняет RebacModelBase для permission Meta. Удален устаревший child_overrides_parent. Бизнес-поля остаются у прежних владельцев, generic timestamps/manager больше не приносятся расширениями.

Resource participants используют штатный ResourceLoadMixin и ровно один super().after_resource_load после своей работы. Demo-only contributors делегируют и при пропуске; ранние выходы seed-логики вынесены в собственные helper-методы. Добавлен integration test install-tier: после пропущенного демо все же создаются accounting journals, sales/purchase sequences, CRM stages/reasons; повторный вызов не дублирует записи.

Обновлены зависимости Hasura/aggregates/REBAC, project addon dependency group пересобран из manifests. Runtime build и schema проходят. Migration diff содержит только AlterModelOptions на VcsBridge, Directory, Organization и Person; столбцы ARPEE не изменились. Перед migrate сохранена SQLite backup .angee/backups/before-native-adaptation.sqlite3; миграции применены. В отдельной пустой SQLite native-cold.sqlite3 прошел полный provision --demo: 437 created, 2 updated. Основная база сохранена.

Первый полный ARPEE backend run на PostgreSQL: 277 tests, 4 errors в Discuss на отсутствующем MessageKind.USER_NOTIFICATION. Удалены два устаревших фильтра (новая enum такого вида не содержит; NOTIFICATION имеет другое назначение и не подставляется вместо него). Повторный Discuss: 21 passed. Native hook regression: 1 passed. Общий framework pytest запущен без ANGEE_PROJECT_DIR и продолжает работу.

Frontend приведен к текущим route href owners, model slot targets, typed MutationDialog.parseValues и TanStack query isFetching; удален устаревший menu sidebar. Host tsconfig задает единую React type identity для связанных checkout. Общий host typecheck и production build проходят. Accounting browser smoke после перезапуска проходит. Компонентные тесты Discuss пока выявляют отдельную проблему двух React runtime в Vitest; диагностика и настройка тестового владельца продолжаются. Финальные результаты будут следующей записью.

## 014 — Итоговые проверки адаптации

**ARPEE:** полный PostgreSQL run — 278 tests, OK (64.689 с), включая новый hook regression и конкурентные accounting/sales/purchase сценарии. Все consumer frontend suites — 81 tests в 23 файлах, passed. Host typecheck и production build проходят. Backend makemigrations --check --dry-run — No changes detected. Ruff измененных Python owners и git diff --check обоих репозиториев проходят.

**Angee:** полный Python run — 1915 passed, 1 failed, 5 skipped (1056.73 с). Единственный failure — новое upstream ожидание вызова hook перед grants в test_native_import_pipeline_rolls_back_all_groups_grants_and_hooks, несовместимое с согласованным hook-after-grants контрактом. Ожидание обновлено; дополнительно инъецирована ошибка hook после успешных grants и проверен rollback rows/M2M/ledger/grants/on_commit. Повторный весь раздел ресурсов с полной collection тестового registry: 48 passed, 1873 deselected. Полный Python набор после изменения только теста второй раз не запускался. Это не следует представлять одним новым полностью зеленым прогоном. При отдельной collection только resource directory отсутствует parties.Handle в upstream test registry; использован `pytest tests addons/angee/resources/tests -k 'test_resources or test_import_pipeline'`, без исключения resource-тестов.

**Frontend test infrastructure:** временные попытки inline всех зависимостей и optimizer с нерезолвящимися прямыми transitive package names не оставлены. Итог: shared Angee Vitest config дедуплицирует React/React DOM/router и обрабатывает logo/Base UI/Floating UI/Lucide через Vite. Discuss test config включает client optimizer с nested dependency specifiers от @angee/ui, в том числе use-sync-external-store shims, чтобы CommonJS peers использовали React тестового host. Дополнительные обходные зависимости не добавлены. Все 17 Discuss frontend tests проходят; весь Angee App frontend suite также прошел — 214 tests, 24 файла. Команда с аргументом config-vitest фактически запустила весь App suite, поэтому фиксируется его реальный результат.

**Данные и браузер:** повторный resources load --include-demo на отдельной холодной базе — 0 created, 0 updated, 439 unchanged. После рестарта основной стек сохраняет прежние демо-данные; invoices/payments/sales/purchase/CRM/calendar/discuss открываются. Проверены реальные CRM карточки, события календаря и открытие general-переписки с историей, без page/GraphQL errors в этих сценариях. Проверен свежий вход alice/alice и форма нового invoice. Анонимная login-страница делает console-запросы с отказами до входа; успешный login это не блокирует. Ранее недоступный фон login теперь отдается 200: Vite fs.allow включает ровно root проекта и явно связанный framework worktree.

Оба сервиса снова running на 0.0.0.0:8601 и 0.0.0.0:5174. Файлы остаются в согласованных worktree: ARPEE modest-toad, framework exotic-pony / astra/invoice-form-contract. Merge/commit/push не выполнялись. Следующие accounting-пакеты (reconciliation graph и posted immutability) не включены в эту адаптацию.

## 015 — Промежуточные коммиты и начало исправления сверки

Пользователь поручил фиксировать промежуточные коммиты и продолжить следующий пакет. Сохранена ранее проверенная адаптация: ARPEE `4e75e5a` (`feat: validate accounting payments and adapt ARPEE to native Angee`), Angee `006ad59d` (`fix: preserve resource dependency order and linked frontend test runtime`). В окружении отсутствует Git identity; для этих коммитов явно использован автор Codex <codex@openai.com>, без изменения глобальной конфигурации. Дальше завершенные шаги фиксируются отдельными коммитами. Git push не выполнялся.

Владелец reconciliation остается `arp.accounting.JournalItemManager`: PartialReconcile хранит связи и суммы, FullReconcile обозначает полностью погашенную связанную компоненту, `JournalItem.reconciled` — нулевой остаток отдельной строки. Ориентир Odoo 19: `_reconcile_plan_with_sync`, `_all_reconciled_lines`, `_compute_amount_residual` в `account_move_line.py`; бизнес-правила реализуются независимо в Django. Соседние sales/inventory уже используют Django atomic и упорядоченные row locks; граф сверки принадлежит accounting, общий графовый framework/зависимость не нужны.

Порядок блокировок для reconcile, unreconcile и Payment.register: Account → все связанные JournalItem → Invoice. Блокировка Account удерживает область графа стабильной во время обхода; на PostgreSQL применяется NO KEY UPDATE, чтобы разрешать внешние ключи при независимом posting. Цена решения — последовательное выполнение сверок одного учетного счета. SQLite не доказывает конкурентную безопасность. Старая логика stamp только выбранных нулевых строк заменяется вычислением компонент; unreconcile удаляет только выбранные связи, затем пересчитывает всю затронутую область. Старые full stamps включаются в область, чтобы не оставлять ложных маркеров у непереданных строк. Корректные existing stamps сохраняются при повторном вызове.

План проверки: 100→40+60; отмена через payment item; один платеж на несколько счетов; credit note + payment; разные независимые компоненты; запрет несовместимых ссылок; rollback регистрации и отмены; конкурентные register/unreconcile на PostgreSQL. Историческая база автоматически не переписывается и массовая миграция сверок не запускается. Изменение статусов/маркеров касается только области явно выполняемой операции.

## 016 — Компоненты сверки реализованы

ARPEE commit `2959b40` (`fix(accounting): reconcile complete payment graphs and refresh all affected debt`) содержит новый обход связей, расчет полной сверки и пересчет после отмены, единый порядок блокировок в Payment.register/reconcile/unreconcile и 14 новых регрессионных тестов. Старый `_stamp_full_reconciles` удален. Валидация проверяет счет, компанию записи и счета, валюту строки и документа, posted state и единого контрагента для receivable/payable; сохранена возможность сверять legacy GL/reversal строки, у которых контрагент отсутствует на обеих сторонах. Несохраненные и исчезнувшие выбранные строки дают ValidationError. Черновая нулевая строка не становится погашенной от вызова unreconcile.

Проверки на PostgreSQL: первый адресный прогон — 40 passed. После добавления принудительного пересечения reconcile/unreconcile и валютного сценария весь backend ARPEE — **291 passed**, 66.119 с. После последнего уточнения для draft/non-reconcilable строк повторный полный accounting-набор — **42 passed**, 6.890 с; весь ARPEE после этого уточнения повторно не запускался. Новый конкурентный тест удерживает первую операцию между созданием matches и обновлением итогов, запускает отмену через исторический endpoint и проверяет ее ожидание, затем остаток 40 и корректные статусы всех трех документов. Также проходят два конкурентных Payment.register и гонка register с отменой предыдущего платежа. В логах остаются существующие предупреждения authlib и сообщения dev-only InMemoryChannelLayer при on_commit публикации тестов; результаты тестов выше относятся к реальному exit 0.

Сборка composed runtime проходит; schema --check — ok; makemigrations --check --dry-run — No changes detected. Ruff E/F/I выполнен с конфигурацией framework (line length 120), git diff --check проходит. Первоначальный lint без этой конфигурации сообщал о существующих длинных строках; они не скрывались новой конфигурацией. В этом пакете frontend-код и контракты API не менялись, frontend suites из предыдущей адаптации не повторялись.

Браузерная проверка после завершения autoreload: invoices, payments и new payment открываются с сохраненной авторизованной сессией, без page errors и HTTP>=400. Первый browser smoke пересекся с autoreload и зафиксировал временные 502; он не считается успешным, повторный лог чистый. Backend /auth/csrf/ и frontend / отвечают HTTP 200. Основная SQLite-база и демо-данные не перезаписывались. Временный PostgreSQL после проверок остановлен.

Следующий пакет по плану — замкнуть защиту проведенных документов на update/delete/bulk/nested пути и проверять агрегат проводок перед posting. Это не входит в `2959b40`; исторические некорректные проводки и reconciliation-компоненты не исправлялись массово. Сериализация по Account остается явно принятым ограничением пропускной способности.

Дополнительно новый модуль запущен отдельно на SQLite: **12 passed, 2 skipped** (только PostgreSQL-тесты блокировок), 0.701 с. Это проверяет ветку без row locks для нашего dev-стека, но не заменяет PostgreSQL-доказательство конкуренции. Журнал и анализ сохранены в Git; gist обновляется вместе с завершенными итерациями.

## 017 — Защита проведенного учета и атомарное проведение

По команде пользователя продолжается следующий пакет. Владелец финансовых правил — accounting; общий Angee не изменяется. Инвентаризация: Entry/Invoice/Payment не защищали все write/delete пути; JournalItem.save не вызывался при bulk update/delete, nested removal использовал `_base_manager`, M2M имеет собственную through-таблицу. Соседние messaging/knowledge используют Django lifecycle signals для каскадных side effects, но signals не закрывают bulk update/create through rows. Поэтому модель дает доменные ошибки, а окончательная неизменность строк реализована database triggers через штатную addon-owned Django runtime migration. Новая зависимость или самодельный общий framework не вводится. Odoo-ориентиры: `account_move._check_balanced`, `write`, `unlink`, `_post`; `account_move_line.write/unlink`. Не воспроизводим неподдерживаемые Odoo lock dates/reopen protocol частично.

`LedgerDocumentMixin` и queryset читают сохраненное состояние, отвергают редактирование/удаление закрытого документа, bulk status changes и создание документа сразу posted. Invoice добавляет только исключение для расчетного payment_status; маркеры сверки JournalItem остаются изменяемыми. Audit references created_by/updated_by разрешено обнулять при удалении пользователя; это не изменяет финансовые факты. API delete_guard делегирует модели. Прежний configurable reopen теперь выдает явную ошибку даже при allow overlay: полноценного протокола обратного проведения нет, использовать reversal.

`post()` Entry и Payment владеют atomic вокруг всей transition, включая final save_state, и блокируют сохраненный draft до materialization/numbering. Для native Invoice явно блокируются дочерняя и родительская таблицы. Child totals сохраняются до смены родительского status в той же транзакции, чтобы не редактировать child уже после posting. Проверяются минимум две ненулевые строки, точный баланс, счета компании, валюта документа/строк/компании, точность сумм, принадлежность журнала, соответствие invoice/bill журналу, company payment term/taxes/distribution accounts. Force-state persistence тоже проверяет агрегат и номер. Nullable counterparty старых plain GL/invoice моделей этим пакетом не меняется; полноценная локализация, правила налоговых распределений и zero-document policy требуют следующих этапов.

Новая self-contained миграция `posted_ledger_guards` создает по три триггера на JournalEntry, Invoice, Payment, JournalItem и through taxes (15 всего): INSERT/UPDATE/DELETE. Запрет касается финансовых изменений любого недрафтового документа, новых строк к нему, переноса строк, удаления и изменения M2M. На PostgreSQL child writes берут NO KEY UPDATE на родительской entry и проверяют ее состояние после ожидания, на SQLite действует сериализация записей. Триггеры защищают неизменность ledger, но не подменяют доменный метод построения проводок для произвольного SQL администратора. Удаление триггеров обратной миграцией не переписывает данные. Модуль сначала проверен на обоих backend, затем зарегистрирован и материализован как `accounting.0006_posted_ledger_guards`; после materialization его source digest не менялся.

Первые проверки: 28 прежних accounting tests проходят; затем 14 новых domain/DB guards tests на PostgreSQL. Первый параллельно начатый второй PostgreSQL run столкнулся с занятой test_postgres и не выполнялся; повторные прогоны запускаются последовательно. В новом GraphQL-тесте первоначально не установились триггеры в отдельном TestCase (он подтвердил nested-delete обход); migration fixture перенесена в общий base для обеих test classes, проверка теперь проходит. Новый API test использует реальных company accountant и read-only member: draft edit разрешен бухгалтеру, читателю запрещен; posted header update/delete/nested line removal отклоняются с сохранением данных. До добавления последнего race test: 57 accounting/reconciliation/ledger tests на PostgreSQL, 15 ledger tests на SQLite — passed.

Прежний reconciliation test намеренно создавал исторически поврежденные posted rows. Теперь его fixture временно обращает миграцию в рамках тестовой транзакции, создает legacy corruption и восстанавливает защиту ДО вызова reconcile. Проверки самого reconcile сохранены; обходы не разрешены в продукте. Добавлен PostgreSQL test: posting удерживается после формирования проводок, параллельный bulk insert ожидает родительский lock и получает IntegrityError после commit. Первый полный ARPEE backend run: 308 passed, 70.012 с. После уточнения блокировки native parent выполняется заключительный полный прогон.

Основная SQLite перед migrate сохранена в `.angee/backups/before-ledger-guards.sqlite3`; миграция применена успешно. Schema --check — ok, makemigrations --check --dry-run — No changes detected; Ruff E/F/I и git diff --check проходят. Старые проводки миграцией не исправляются и не перепроводятся. Frontend-код и SDL-контракт не менялись.

## 018 — Пакет защиты завершен и закоммичен

ARPEE commit **`bcf604f`** (`fix(accounting): guard posted ledger writes and make posting atomic`). Заключительный полный backend ARPEE на PostgreSQL после всех изменений — **308 passed, 69.016 с**. Это включает 16 новых ledger tests, прежние payment/reconciliation tests, API проверки company accountant/reader и PostgreSQL posting-vs-bulk-insert race. Последний SQLite ledger run — **15 passed, 1.953 с**, до добавления PostgreSQL-only race и уточнения `of=()` (на SQLite ветка без row locks не менялась). Никакие тесты продукта не отключались; разрешение создавать поврежденные legacy records существует только в fixture с восстановленной защитой до проверки бизнес-операции.

`angee build --check` — ok, миграционная история и source digest согласованы. Сравнение основной SQLite с backup через двусторонний EXCEPT подтверждает отсутствие изменений в JournalEntry, Invoice, Payment, JournalItem, through taxes, PartialReconcile, FullReconcile. Установлены 15 триггеров. PRAGMA integrity_check через Django connection возвращает ok; первый вызов через голый sqlite3 не смог проверить существующую generated MD5 column, поскольку функции Django в таком соединении не зарегистрированы — это устранено использованием штатного соединения, данные не ремонтировались.

Browser smoke с сохраненной сессией: invoices/payments/new payment открываются без page errors, HTTP>=400 и redirect на login. Backend /auth/csrf/ и frontend / — HTTP 200; оба сервиса running. Временный PostgreSQL остановлен. Новые финансовые поля или перестроение защищенных таблиц требуют новой migration защиты; опубликованный/материализованный origin не редактировать. Эта инструкция добавлена в `docs/accounting-dev.ru.md` владельца ARPEE. Git push не выполнялся; изменения сохранены локальными промежуточными коммитами, журнал публикуется в существующий gist.

## 019 — Налоги, первый из двух последовательных шагов

Пользователь запросил налоги и график платежей, затем уточнил «one by one». После прерывания до вопроса «working?» изменений этого пакета еще не было; это явно сообщено. Текущая итерация посвящена налогам, график платежей не изменяется.

Инвентаризация владельцев обнаружила одинаковую ошибку в Invoice, SalesOrderLine и PurchaseOrderLine: последовательный net_of_included на нескольких налогах уменьшал базу повторно. Odoo 19 `_eval_tax_amount_price_included` в `account_tax.py` использует сумму процентов общего batch; `_eval_tax_amount_fixed_amount` считает фиксированный сбор от количества независимо от скидки. Независимая Django-реализация принадлежит TaxQuerySet: price×quantity×(1−discount) = base×(1+sum(included rates)) + included fixed charges. Стратегии TaxCompute предоставляют коэффициент базы и фиксированную часть через included_terms; типы не распознаются по строкам в Invoice/заказах. Старый single-tax net_of_included сохранен как совместимый API, но не используется для расчета наборов. Нелинейная или каскадная стратегия обязана явно расширить контракт; скрытого последовательного fallback нет.

TaxLine хранит результат расчета и округляет документ по политике компании. В per_document сначала округляется общий налог, затем его доли распределяются по строкам в единицах валюты; при равных дробных остатках применяется стабильный порядок строк. Включенная gross-сумма сохраняется: округленная база = округленная введенная сумма минус включенные налоги. Это закрывает и копеечный случай 0.05 с двумя включенными 10%, где независимое округление базы и налогов теряло цент. TaxAmounts реализует настоящее распределение по наибольшему дробному остатку; прежняя коррекция всей разницы в строку с максимальным процентом удалена.

Sales/Purchase используют тот же расчет. При пересчете заказа сохраняются согласованные суммы всех строк и шапки, включая per_document, вместо суммирования независимо округленных previews. Объект сохраняемой строки обновляет свои amount-поля после распределения, чтобы GraphQL/вызывающий код не получали прежний preview. Пример регрессии: включенный 10%, строки 0.03 и 0.04 → налог 0.01, база 0.06, итого 0.07; вторая строка возвращает базу 0.03 и итог 0.04 сразу после save.

Tax.posting_distributions требует для выбранной стороны invoice/refund положительные доли в сумме 100% и явные счета компании документа. Отсутствие распределений, 90/110%, отрицательная доля и пустой счет не маскируются округлением или default account журнала. Проверяется активная сторона распределения; ошибка в неиспользуемой refund-настройке не блокирует обычный invoice, но блокирует refund. Отрицательные ставки/удержания и отрицательные factors не поддерживались прежним nonnegative GL; теперь неподдерживаемая ставка дает явную ValidationError. Это не заявление о полном налоговом parity Odoo или локализации.

Первые адресные проверки — 102 passed на PostgreSQL. После расширения сценариев (14 новых tax tests) полный ARPEE backend — 322 passed, 71.903 с; отдельный tax module на SQLite — 14 passed, 0.586 с. Сценарии: 120→100+10+10 для всех четырех invoice/refund видов, правильные знаки долга, fixed+percent в обоих порядках, quantity/discount, included+excluded, per_line/per_document, валюта с тремя десятичными знаками, распределение округления по счетам, rollback неправильной настройки, одинаковые суммы accounting/sales/purchase. После уточнения возврата округленных amount-полей из save выполняется финальный адресный accounting/sales/purchase прогон.

Новых полей/миграций нет; makemigrations --check — No changes detected, schema --check — ok. Browser invoices/payments/new payment проходит с авторизованной сессией без page errors/HTTP>=400. Framework-код и frontend-код не изменены; существующие проведенные документы не пересчитываются, сохраненные ранее draft/order totals обновляются при обычном save/recompute/post. Общий расчет и ограничения описаны в ARPEE docs/accounting-dev.ru.md.

## 020 — Налоговый шаг завершен

ARPEE commit **`a8d9b13`** (`fix(accounting): compute included taxes jointly and preserve rounded totals`). Финальный адресный accounting/sales/purchase/tax прогон после уточнения возвращаемых из save сумм — **104 passed, 18.675 с**. Предшествующий полный ARPEE прогон — 322 passed; полный набор после изменения только возврата amount-полей не повторялся. SQLite tax module — 14 passed. Ruff E/F/I, git diff --check и angee build --check проходят; миграций и изменений SDL нет. Backend/frontend отвечают HTTP 200; временный PostgreSQL остановлен.

Налоги зафиксированы отдельным шагом согласно «one by one». PaymentTerm/график задолженности не изменялся и остается следующим пакетом. Рабочее дерево ARPEE после коммита чистое; журнал решений публикуется в тот же gist и сохраняется отдельным docs-коммитом Angee. Git push не выполнялся.

## 021 — Partner в списке счетов (2026-09-06)

По запросу пользователя в общий InvoiceWorkbench добавлена декларация Column для partner после номера документа. Используется существующий relation renderer и перевод col.partner. Колонка доступна в Customer Invoices и Vendor Bills, использующих один компонент. Backend, schema и миграции не изменялись.

ARPEE commit **`6b1be0f`** (`feat(accounting): show partner in invoice lists`). Авторизованный browser smoke подтвердил заголовок Partner и заполненные названия контрагентов. Страницы invoices/payments/new payment открылись без page errors и HTTP>=400; git diff --check прошел. Для однострочной декларации новые тесты не добавлялись.

Первая попытка публикации была отклонена автоматической проверкой разрешений. Пользователь затем явно подтвердил публикацию этой записи и результатов проверки в существующий gist 44d67e5f0e656dbce5366693082b88dc сообщением «go».
