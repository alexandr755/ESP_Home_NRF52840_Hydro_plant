# Manual: сборка и прошивка ESPHome-датчика влажности (NRF52840, Zigbee)

Пошаговая инструкция «что за чем делать» — для себя на будущее, без Claude под рукой.

## Общая схема

```
Windows: редактирование .yaml (humidy-zeegbe-plant1.yaml)
        ↓ (копирование)
WSL2 Ubuntu: компиляция ESPHome/Zephyr → .uf2
        ↓ (копирование обратно)
Windows: прошивка платы через UF2 (drag-and-drop)
```

Почему так сложно: компиляция ESPHome для NRF52840 (Zephyr) не работает напрямую в Windows (см. `CLAUDE.md`, Problem 3), поэтому используется WSL2. А внутри WSL2 нельзя собирать прямо в `/mnt/c/...` (Windows-диск) — там своя ошибка (Problem 4). Поэтому проект компилируется из отдельной копии внутри самого WSL.

---

## 1. Редактирование конфига

Редактируешь как обычно в Windows:
```
C:\PlatformIO\Projects\ESP_Home_NRF52840_Hydro_plant\humidy-zeegbe-plant1.yaml
```

## 2. Скопировать конфиг в WSL

Открой PowerShell и выполни:
```powershell
wsl.exe -d Ubuntu-26.04 -- bash -lc "cp /mnt/c/PlatformIO/Projects/ESP_Home_NRF52840_Hydro_plant/humidy-zeegbe-plant1.yaml ~/esphome-projects/hydro-plant/"
```

## 3. Скомпилировать

```powershell
wsl.exe -d Ubuntu-26.04 -- bash -lc "source ~/esphome-venv/bin/activate && cd ~/esphome-projects/hydro-plant && esphome compile humidy-zeegbe-plant1.yaml"
```

- Первая компиляция после смены версии/ядра Zephyr может занять 10-20 минут (скачивание nRF Connect SDK).
- Обычная (инкрементальная) компиляция — быстрее, минуты.
- В конце должно быть: `INFO Successfully compiled program.`
- Если ошибка — читай traceback, часто это баг конфигурации YAML, а не среды.

## 4. Скопировать готовую прошивку обратно в Windows

```powershell
wsl.exe -d Ubuntu-26.04 -- bash -lc "cp ~/esphome-projects/hydro-plant/.esphome/build/single-flower-monitor/.pioenvs/single-flower-monitor/zephyr/zephyr.uf2 /mnt/c/PlatformIO/Projects/ESP_Home_NRF52840_Hydro_plant/single-flower-monitor.uf2"
```

Файл `single-flower-monitor.uf2` появится в корне проекта в Windows.

> Если имя устройства в `esphome:` -> `name:` в yaml изменится, путь `.../build/<имя>/...` тоже изменится — подставь новое имя.

## 5. Прошить плату (UF2)

1. Подключи ItsyBitsy NRF52840 к компьютеру по USB.
2. Дважды быстро нажми кнопку **Reset** на плате — она должна перезагрузиться в режим UF2-bootloader и появиться в Windows как съёмный диск (обычно называется `ITSYBOOT` или похоже).
3. Перетащи (или скопируй) `single-flower-monitor.uf2` на этот диск.
4. Плата автоматически прошьётся и перезапустится в обычном режиме — диск исчезнет.

Если диск не появляется — проверь USB-кабель (должен быть с поддержкой данных, не только питания) и попробуй ещё раз двойной Reset — таймаут окна для двойного клика короткий (~0.5 сек).

## 6. Проверить подключение к Zigbee2MQTT

- Открой логи платы (см. ниже) или интерфейс Z2M → включи режим "Permit join" → плата должна появиться в списке устройств Z2M.
- Убедись, что Z2M версии ≥ 2.8.0 (см. предупреждение при компиляции про single endpoint).

## 7. Смотреть логи через USB (подтверждено рабочим)

Логи — это просто чтение serial-порта, компилятор/WSL для этого не нужен. Работает прямо из Windows через уже установленный там ESPHome (2026.6.3), без usbipd и без WSL.

**Шаг 1 — найти COM-порт платы:**
```powershell
Get-PnpDevice -Class Ports -PresentOnly | Select-Object Status, Class, FriendlyName, InstanceId | Format-List
```
Ищи устройство `USB\VID_2FE3&PID_0100...` ("Устройство с последовательным интерфейсом USB") — это стандартный VID/PID проекта Zephyr для USB CDC ACM, который использует эта прошивка. В `FriendlyName` увидишь номер порта, например `COM7`.

**Шаг 2 — запустить лог:**
```powershell
$env:PYTHONUTF8 = "1"
esphome logs humidy-zeegbe-plant1.yaml --device COM7
```
(подставь свой номер COM-порта).

**Важные нюансы:**
- Если подключиться к логам уже ПОСЛЕ загрузки платы — самые ранние сообщения загрузки (включая сигналы Zigbee-подключения `ZB_BDB_SIGNAL_DEVICE_FIRST_START`, `ZB_BDB_SIGNAL_STEERING`) будут упущены — нет буфера для "опоздавших" слушателей. Чтобы поймать полный лог загрузки, сначала запусти команду логов, а потом перезагрузи плату (обычный Reset, не двойной клик в bootloader).
- При перезагрузке/переподключении USB лог обрывается с `ERROR Serial port closed!` — это нормально, просто перезапусти команду.

## 8. Внешний конвертер для Z2M (чтобы устройство не было "Not supported" и влажность отображалась в %)

По умолчанию Z2M видит устройство как `Not supported: generated` и сыпет в лог `No converter available for '' on '<IEEE>': (undefined)` при каждом отчёте с платы. Кнопка "Generate external definition" в Dev console — это только предпросмотр, реально ошибку убирает только сохранённый файл конвертера + рестарт Z2M.

**Готовый конвертер лежит в репозитории:** `zigbee2mqtt-external-converters/single-flower-monitor.js`. Использует кластер `genAnalogInput` / атрибут `presentValue`, `name: 'humidity'` (важно — именно по этому имени Z2M/HA автоматически определяют `device_class` и показывают объект как измеритель влажности), `scale: 0.01` (пересчёт сырой доли 0-1 в проценты).

**Как применить через File Editor / Studio Code Server (мой обычный способ доступа к HA):**

1. Открой File Editor (или Studio Code Server) add-on в Home Assistant.
2. Найди папку конфигурации Zigbee2MQTT — обычно видна в дереве файлов как `zigbee2mqtt/` (рядом с `configuration.yaml`), либо через Studio Code Server с полным доступом к файловой системе — в `/addon_configs/<slug>_zigbee2mqtt/`.
3. Внутри неё создай (если ещё нет) папку **`external_converters`**.
4. Создай файл **`single-flower-monitor.js`** и вставь содержимое из `zigbee2mqtt-external-converters/single-flower-monitor.js` в этом репозитории.
5. **Settings → Add-ons → Zigbee2MQTT → Restart.**
6. Проверь:
   - В **Exposes** должна появиться сущность `Soil moisture` в %.
   - В Home Assistant объект должен определиться как сенсор влажности (иконка капли, `%`).
   - В **Logs** ошибки `No converter available` должны исчезнуть.

Если при рестарте Z2M выдаст `SyntaxError: Cannot use import statement outside a module` — эта версия Z2M ждёт ESM-файлы с расширением `.mjs`, а не `.js`; переименуй файл.

> При изменении конфига датчика (например, добавление battery/switch эндпоинтов) конвертер, скорее всего, тоже придётся обновить — новые эндпоинты/кластеры не появятся в нём автоматически.

---

## Частые проблемы

| Симптом | Причина | Что делать |
|---|---|---|
| `PermissionError: os.fchmod` при компиляции | Собираешь прямо в `/mnt/c/...` | Убедись, что используешь копию в `~/esphome-projects/hydro-plant/`, а не оригинал на Windows-диске |
| `FileNotFoundError: WinError 2` | Пытаешься компилировать на голом Windows (без WSL) | Всегда компилируй через WSL2, см. шаги выше |
| Плата не подключается к Z2M | `sleepy: true` включён до подтверждения пейринга | В конфиге держи `sleepy: false`, пока пейринг не подтверждён (см. CLAUDE.md) |
| После прошивки плата не шлёт данные повторно | `update_interval: never` | Используй реальный интервал, например `60s` для теста |
| Диск UF2-bootloader не появляется | Слишком медленный/быстрый двойной клик Reset, либо кабель без данных | Повтори двойной клик, смени кабель |

---

## Следующие шаги проекта (roadmap)

1. ✅ Плата собирается и компилируется через WSL2
2. ✅ Пейринг с Z2M подтверждён (Z2M обновлён до 2.12.1, устройство видно как `single-flower-monitor`)
3. ✅ Данные с датчика доходят до Z2M и корректно отображаются в HA как "Soil moisture" в % (внешний конвертер применён, см. шаг 8)
4. ⬜ Добавить управление питанием датчика (GPIO switch, `sensor_vcc_power` на `P0.08`) на каждый цикл измерения
5. ⬜ Добавить мониторинг батареи (voltage divider на свободный AIN)
6. ⬜ Включить `deep_sleep` (например, 60 минут) — только после того как Zigbee-пейринг подтверждён и `sleepy: true` включён и тоже подтверждён рабочим
