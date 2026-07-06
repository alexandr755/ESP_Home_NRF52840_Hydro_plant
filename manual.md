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

## 7. Смотреть логи (опционально, для отладки)

Через USB (пока не включён `sleepy: true` / deep_sleep):
```bash
# из WSL, с активированным venv
esphome logs humidy-zeegbe-plant1.yaml
```
(Может потребоваться проброс USB-устройства в WSL через usbipd-win — иначе логи проще смотреть штатным способом из Windows-инструмента ESPHome, если он установлен, либо через serial-monitor.)

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
2. ⬜ Подтвердить пейринг с Z2M (без физического датчика)
3. ⬜ Добавить управление питанием датчика (GPIO switch, `sensor_vcc_power` на `P0.08`) на каждый цикл измерения
4. ⬜ Добавить мониторинг батареи (voltage divider на свободный AIN)
5. ⬜ Включить `deep_sleep` (например, 60 минут) — только после того как Zigbee-пейринг подтверждён и `sleepy: true` включён и тоже подтверждён рабочим
