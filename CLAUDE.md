# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ESPHome firmware for a 4-plant soil moisture monitor (one board, 4 independent sensors). Target hardware: **SuperMini NRF52840** (ProMicro-form-factor nRF52840-QIAA clone board — NOT a genuine Adafruit ItsyBitsy; the `nrf52: board: adafruit_itsybitsy_nrf52840` value in the yaml is just the closest available Zephyr board definition ESPHome offers and happens to compile/work, it does not describe the physical board). Corrected 2026-07-09 after reading the board's actual schematic/pinout (`schema.jpg`, seller pinout screenshots) — see "SuperMini NRF52840 Hardware Notes" below. Communicates over **Zigbee** (End Device), integrated with **Home Assistant** (ZHA, see below — moved off the original Z2M network for range reasons).

Sensor: 4x capacitive soil moisture v1.2 (analog output), powered via the board's built-in VCC switch (P0.13, shared across all 4 sensors — not yet wired).
Power: Li-ion battery (18650) via the board's **built-in** TP4054 charger — no external TP4056 module (superseded plan, do not add one, see below).

---

## ESPHome Commands

```bash
# Validate config
esphome config humidy-zeegbe-plant1.yaml

# Compile only (get .bin)
esphome compile humidy-zeegbe-plant1.yaml

# Compile + flash via USB
esphome run humidy-zeegbe-plant1.yaml

# Stream logs
esphome logs humidy-zeegbe-plant1.yaml
```

**Installed ESPHome version:** 2026.6.3 (Windows PC)

---

## Known Issues — Windows Build Environment

### Problem 1: Unicode crash in PlatformIO output
The username path `C:\Users\Александр\` contains Cyrillic. PlatformIO tries to decode build output as UTF-8 and crashes.

**Fix:** always set before compiling:
```powershell
$env:PYTHONUTF8 = "1"
chcp 65001
esphome compile humidy-zeegbe-plant1.yaml
```

### Problem 2: Zephyr SDK install.py has Windows bugs (FIXED)
`C:\.platformio\packages\toolchain-gccarmnoneeabi\install.py` had two bugs:
- Used `AMD64` but GitHub releases use `x86_64`
- Used `.tar.xz` but Windows releases are `.7z`

**Already fixed** in `install.py` — it now uses 7-Zip (`C:\Program Files\7-Zip\7z.exe`) and correct filenames. The Zephyr SDK v0.17.4 is installed at `C:\.platformio\packages\toolchain-gccarmnoneeabi\zephyr-sdk-0.17.4\`.

**Do not delete** `C:\.platformio\packages\toolchain-gccarmnoneeabi\toolchain_installed` — that marker tells the installer the SDK is already present.

### Problem 3: west manifest + git WinError 2 (WORKED AROUND — build in WSL2)
During CMake, `zephyr_module.py` calls `west.manifest.Manifest.from_file()` which tries to call `git` with `cwd` pointing to non-existent project directories. On Windows this raises `FileNotFoundError: [WinError 2]`.

Root cause: west version installed doesn't guard against non-existent `cwd` before spawning git subprocess.

**Resolution:** Compile in WSL2 (Ubuntu-26.04) instead of native Windows. Confirmed working — see "Building in WSL2" below.

### Problem 4: WSL2 + DrvFs (`/mnt/c/...`) breaks ESPHome file writes (RESOLVED — build outside /mnt/c)
Even inside WSL2, if the project lives under `/mnt/c/...` (a Windows drive mounted via DrvFs), ESPHome crashes when writing `storage_json`:
```
PermissionError: [Errno 1] Operation not permitted
  os.fchmod(f_handle.fileno(), 0o644)
```
DrvFs does not support fd-based `fchmod` (only path-based `chmod`), and ESPHome's `helpers.py` calls the fd-based variant.

**Fix:** keep the working build copy inside the WSL Linux filesystem (e.g. `~/esphome-projects/hydro-plant/`), not under `/mnt/c`. This is also faster since DrvFs I/O from WSL2 is slow.

---

## Building in WSL2 (working setup, confirmed 2026-07-06)

Ubuntu-26.04 installed via `wsl.exe --install Ubuntu-26.04`. ESPHome lives in a venv at `~/esphome-venv` inside WSL — separate from the Windows install. The build working copy is `~/esphome-projects/hydro-plant/`, a plain copy of the `.yaml` config (NOT a symlink/mount of `/mnt/c`, see Problem 4 above).

**Every time the `.yaml` config changes**, copy the updated file into WSL before compiling:
```powershell
wsl.exe -d Ubuntu-26.04 -- bash -lc "cp /mnt/c/PlatformIO/Projects/ESP_Home_NRF52840_Hydro_plant/humidy-zeegbe-plant1.yaml ~/esphome-projects/hydro-plant/"
```

**Compile:**
```powershell
wsl.exe -d Ubuntu-26.04 -- bash -lc "source ~/esphome-venv/bin/activate && cd ~/esphome-projects/hydro-plant && esphome compile humidy-zeegbe-plant1.yaml"
```

First compile downloads the full nRF Connect SDK (Zephyr v2.6.1) via `west update` — many git submodules, takes 10-20 minutes. Subsequent compiles are much faster (incremental).

**Compiled firmware output** (inside WSL):
```
~/esphome-projects/hydro-plant/.esphome/build/flower-monitor/.pioenvs/flower-monitor/
├── firmware.hex / firmware.elf
└── zephyr/{zephyr.hex, zephyr.bin, zephyr.uf2, merged.hex}
```
(build directory name = `esphome: name:` in the yaml — it was `single-flower-monitor` before the 4-sensor redesign, now `flower-monitor`)

**Copy firmware back to Windows** (for flashing via UF2 drag-and-drop):
```powershell
wsl.exe -d Ubuntu-26.04 -- bash -lc "cp ~/esphome-projects/hydro-plant/.esphome/build/flower-monitor/.pioenvs/flower-monitor/zephyr/zephyr.uf2 /mnt/c/PlatformIO/Projects/ESP_Home_NRF52840_Hydro_plant/flower-monitor.uf2"
```

See `manual.md` for the full step-by-step workflow.

---

## Reading Logs via USB (COM port, confirmed working 2026-07-06)

Log streaming does **not** need the Zephyr/west toolchain — it's just a serial monitor, so it works fine with the existing **Windows** ESPHome install (2026.6.3), no WSL needed.

**1. Find the board's COM port:**
```powershell
Get-PnpDevice -Class Ports -PresentOnly | Select-Object Status, Class, FriendlyName, InstanceId | Format-List
```
Look for a `USB\VID_2FE3&PID_0100...` entry (`Устройство с последовательным интерфейсом USB`) — VID `2FE3`/PID `0100` is the default Zephyr Project USB CDC ACM sample VID/PID, which this firmware uses. Note the `COMx` name shown in `FriendlyName`.

**2. Stream logs:**
```powershell
$env:PYTHONUTF8 = "1"
esphome logs humidy-zeegbe-plant1.yaml --device COM7
```
(replace `COM7` with whatever port was found in step 1). `PYTHONUTF8` is needed for the same Cyrillic-path reason as Problem 1 above.

**Notes:**
- Logger's default `hardware_uart` on nrf52 is `USB_CDC` — logging over USB works out of the box, no extra config needed.
- If you attach the monitor *after* the board already booted, you miss the earliest boot messages (no ring buffer for late-attaching serial listeners) — power-cycle/reset the board while the monitor is already running to capture full boot logs, including Zigbee join/steering signals (`ZB_BDB_SIGNAL_DEVICE_FIRST_START`, `ZB_BDB_SIGNAL_STEERING`).
- On board reset/USB re-enumeration the terminal prints `ERROR Serial port closed!` and exits — this is expected, just restart the log command.

---

## Zigbee2MQTT External Converter (confirmed working 2026-07-06)

A fresh ESPHome zigbee device shows up in Z2M as `Not supported: generated` and spams `No converter available for '' on '<IEEE>': (undefined)` in the logs on every attribute report. The Dev console's "Generate external definition" button is preview-only — it does **not** fix this until the generated code is saved as a real file and Z2M is restarted.

**Converter source of truth:** `zigbee2mqtt-external-converters/flower-monitor.js` in this repo (ESM syntax — `import`/`export default`, matching what Z2M 2.12.1 itself generates). Uses `m.numeric()` from `modernExtend` against `genAnalogInput`/`presentValue`, with `name: 'humidity'` (Z2M/HA special-case this exact name to assign the humidity `device_class` automatically) and `scale: 0.01` (raw ADC ratio 0-1 → percent).

**Multi-endpoint (4 sensors, since the redesign):** each sensor is a separate Zigbee endpoint (1-4), same cluster/attribute on each. Handled via the device-level `endpoint: (device) => ({flower_1: 1, flower_2: 2, flower_3: 3, flower_4: 4})` mapping plus `endpointNames` on the `numeric()` call — standard zigbee-herdsman-converters pattern for multi-gang devices. Resulting exposed properties are suffixed per endpoint (e.g. `humidity_flower_1`). **Not yet verified against a real re-pairing** — after flashing the 4-sensor firmware, re-run "Generate external definition" in Dev console once the device re-joins, and cross-check endpoint numbers actually match declaration order in the yaml (assumed sequential 1-4 by sensor order, unconfirmed).

**Deployment (user accesses HA via File Editor / Studio Code Server add-on):**
1. Copy the file into the Z2M add-on's `external_converters/` folder (visible as `zigbee2mqtt/` next to `configuration.yaml`, or under `/addon_configs/<slug>_zigbee2mqtt/` via Studio Code Server with full filesystem access). Delete the old `single-flower-monitor.js` there too if present.
2. Restart the Zigbee2MQTT add-on.
3. If Z2M throws `SyntaxError: Cannot use import statement outside a module`, this Z2M version expects `.mjs` instead of `.js` — rename the file.

**Gotcha:** if the device config gains more endpoints (e.g. battery sensor, switch), the converter needs matching updates — new clusters won't auto-appear in it.

See `manual.md` step 8 for the full walkthrough.

**Status update (2026-07-07):** the board doesn't reliably reach this coordinator from the far room. See "ZHA Second Coordinator" below — the board currently runs on a *different* network (ZHA via a second coordinator), not this Z2M one. This Z2M converter section is kept for reference / in case the board moves back to the primary network (e.g. once a Zigbee router is added per `plain.md`).

---

## ZHA Second Coordinator (Bridge Pro) + Custom Quirk (confirmed working 2026-07-07)

**Background:** the board couldn't reach the primary Z2M coordinator from the far room (see `plain.md` for the range-extension plan — router options via CC2531/CC-Debugger or Bridge Pro). Instead of/in addition to a router, the user stood up a **second, independent Zigbee network**: SONOFF Zigbee Bridge Pro flashed with Tasmota + Zigbee coordinator firmware, added to Home Assistant as a native **ZHA** integration ("Generic Zigbee Coordinator (EZSP)"). This is a second network, not a mesh extension of the first — see `plain.md` Вариант В for the tradeoffs (WiFi-based serial-to-IP bridges are officially discouraged by Z2M docs; same caveat applies conceptually here).

**The board is now paired to this second (ZHA) network, not the original Z2M one.**

### Rejoining a different network
The board remembers whichever network it last joined (stored in flash). To make it forget and rejoin a *different* network:
1. Set `wipe_on_boot: once` in the yaml (temporarily — see note below), then recompile. Each `esphome compile` with `once` generates a fresh random magic number, which forces a wipe+rejoin on the firmware's next boot.
2. Reflash via UF2.
3. **Disable Permit Join on the network you don't want it to join, enable it only on the target network** — if both networks have Permit Join open simultaneously, which one the board joins is not guaranteed.
4. Power on — board wipes its Zigbee state and joins whichever network has Permit Join active.
5. Afterwards, set `wipe_on_boot` back to `false` and recompile/reflash once more — see note below.

**Default is `wipe_on_boot: false` (changed 2026-07-09).** With `once`, *every* recompile (even for unrelated changes like adding a sensor) generates a new magic number and forces a rejoin on next boot — annoying once the board is already stably paired. Only switch to `once` temporarily when you actually want to force a rejoin (e.g. moving to a different network, per steps above); otherwise leave it on `false` so routine firmware updates don't disturb the existing pairing.

### Custom ZHA quirk (equivalent of the Z2M external converter, different ecosystem)
A fresh device on ZHA shows generic sensor entities named `__1`..`__4` (raw ADC ratio, unit "V", wrong) instead of proper humidity/percent sensors — ZHA's default fallback for an unrecognized `genAnalogInput`/`AnalogInput` cluster, same underlying problem as Z2M's `Not supported: generated`. ZHA's equivalent of an "external converter" is a Python **quirk**, using the modern `QuirkBuilder` fluent API (`zigpy.quirks.v2`).

**Quirk source of truth:** `zha-quirks/esphome_flower_monitor.py` in this repo. Matches by `QuirkBuilder("esphome", "flower-monitor")` (manufacturer/model exactly as read from the live device's Basic cluster — visible in HA's device card). Defines 4 `.sensor()` calls, one per endpoint (1-4), each:
- `"present_value"` attribute (snake_case zigpy convention for ZCL `presentValue`) on `AnalogInput.cluster_id` (0x000C = `genAnalogInput`)
- `multiplier=100, divisor=1` — raw 0-1 ratio → percent (matches the `scale: 0.01` used in the Z2M converter, same math, different parameter name/direction)
- `device_class=SensorDeviceClass.HUMIDITY`, `unit="%"`, `state_class=SensorStateClass.MEASUREMENT`
- `suggested_display_precision=0` — rounds the HA frontend display to whole percent (doesn't touch the stored/logged value)

**Deployment:**
1. Create `/config/zha_quirks/` (from **Home Assistant Core's own internal path perspective** — this is `/config` regardless of what a file-management tool's UI shows as the absolute path, e.g. an SSH/Terminal add-on may display the same folder as `/homeassistant/...`; what matters is it's the same folder that already contains `configuration.yaml`).
2. Copy `esphome_flower_monitor.py` into it.
3. In `configuration.yaml`:
   ```yaml
   zha:
     enable_quirks: true
     custom_quirks_path: /config/zha_quirks/
   ```
4. **Full HA restart** (not just YAML reload) — quirks only load at startup.

**Gotchas:**
- If HA complains `not a directory for dictionary value 'zha->custom_quirks_path'`, the folder doesn't physically exist yet at that path — create it first via Studio Code Server / File Editor, then restart.
- The old generic `__1`..`__4` entities **don't disappear** after adding the quirk — they were already registered in HA's entity registry before the quirk existed, and HA doesn't retroactively remove them. HA also won't let you **delete** them outright while ZHA is still actively providing them (a live-integration entity) — only **disable** them (Settings → Devices & services → Entities → select → disable). Disabling is sufficient (hides from dashboards, stops updating). If this recurs after a future re-interview, the fix would be adding `.replaces()` with a custom cluster class in the quirk to fully take over the cluster instead of just adding a `.sensor()` on top — not yet needed/tried.

---

## Zigbee Configuration Notes

### ESPHome validation rule
`zigbee:` component requires at least one sensor/entity — bare `zigbee:` alone fails with:
> "At least one zigbee device need to be included."

Always keep at least the ADC sensor in the config even during connectivity testing.

### sleepy: true breaks initial pairing
`zigbee: sleepy: true` (Sleepy End Device mode) prevents Z2M from completing the pairing handshake. Use `sleepy: false` until pairing is confirmed working. Re-enable only after deep_sleep is also configured.

### on_boot priority and update_interval
- Boot sequence (sensor power → read → power off) must run at `priority: -100` (after all components init), not `priority: 600` (too early, Zigbee not joined yet).
- `update_interval: never` means sensor reads once at boot then never again. After Zigbee joins, nothing is reported. Use a real interval (e.g. `60s` for testing, `60min` for production).

### Z2M version warning
ESPHome warns: *"Single endpoint requires ZHA or at least Zigbee2MQTT 2.8.0"*. This is informational — ensure Z2M ≥ 2.8.0.

---

## SuperMini NRF52840 Hardware Notes (confirmed 2026-07-09)

Real board is a **SuperMini NRF52840** ProMicro-form-factor clone (chip: nRF52840-QIAA), not a genuine Adafruit ItsyBitsy. Confirmed from the seller's schematic (`schema.jpg`) and pinout diagrams (`Screenshot_5.jpg`–`Screenshot_8.jpg`) checked into the repo root.

- **Built-in Li-Po/Li-ion charger:** TP4054 linear charger IC. Solder battery to the `BATTERY+` / `B-` pads directly (no external TP4056 needed — do not wire one in parallel, two chargers fighting over the same cell is unsafe).
- **Charge current jumper `BOOST`:** unbridged = 100mA charge current; solder-bridge the `BOOST` pad (next to VCC/RST) to raise it to 300mA. Seller explicitly says only bridge this if battery capacity > 500mAh — an 18650 (typically 2000mAh+) qualifies, bridging is appropriate (100mA on an 18650 would take ~20h+ to charge).
- **Built-in switched VCC rail:** `P0.13` drives an onboard MOSFET gating the `VCC` (3.3V) pin — HIGH = VCC powered, LOW = VCC cut off. This **replaces** the originally-planned external GPIO+FET sensor power switch: wire all 4 soil sensors' VCC lines to the board's `VCC` pin (not directly to battery/3V-always-on), and use `P0.13` as an ESPHome `switch: platform: gpio` to power them only during a reading. (`P0.08`, previously reserved for this, is no longer needed for it — free.)
- **No populated battery-voltage divider.** The schematic shows `BAT` routed only to unpopulated NC test pads — battery% needs a hand-added external resistor divider (see Pin Map below).
- Physical GPIO breakout is **much sparser** than ItsyBitsy — only specific pins are brought to header holes: `P0.02(AIN0)/D19, P0.06/D1, P0.08/D0, P0.09, P0.10, P0.11/D7, P0.17/D2, P0.20/D3, P0.22/D4, P0.24/D5, P0.29(AIN5)/D20, P0.31(AIN7)/D21, P1.00/D6, P1.01, P1.02, P1.04/D8, P1.06/D9, P1.07, P1.11, P1.13, P1.15`, plus `VCC`, `RST`, `GND`×several, `BATTERY+`×2, and the SWD debug pins (`VDD/DIO/CLK/GND`). Notably `P0.03/P0.04/P0.05` (AIN1-3, used by `flower_2`-`flower_4` in the working config) are **not** on this list — they were evidently hand-soldered directly to the chip pads/vias rather than a header pin. Keep this in mind before assuming any pin is accessible without fine SMD soldering — check against this list first.

## Pin Map

Analog-capable header pins actually broken out on this board: `P0.02=AIN0=D19`, `P0.29=AIN5=D20`, `P0.31=AIN7=D21` (plus `P0.03/P0.04/P0.05=AIN1-3`, hand-soldered directly to chip pads for this project, not header pins).

| ESPHome ID | Physical pin | Role |
|---|---|---|
| `sensor_vcc_power` | `P0.13` | Built-in VCC MOSFET switch — sensor power enable (planned, shared across all 4 sensors — not yet wired) |
| `flower_1` (ADC) | `P0.02` (AIN0 / D19, header pin) | Soil moisture sensor 1 |
| `flower_2` (ADC) | `P0.03` (AIN1, hand-soldered to chip pad) | Soil moisture sensor 2 |
| `flower_3` (ADC) | `P0.04` (AIN2, hand-soldered to chip pad) | Soil moisture sensor 3 |
| `flower_4` (ADC) | `P0.05` (AIN3, hand-soldered to chip pad) | Soil moisture sensor 4 |
| battery monitor | `P0.31` (AIN7 / D21, header pin) planned | External voltage divider from `BATTERY+` — not yet wired |

Free/spare after the above: `P0.29` (AIN5/D20), `P0.08` (D0, no longer needed for sensor power now that `P0.13` covers it).

**`dcdc: false`** — must stay off; this board has no external inductor for the DC/DC converter. Without this flag the board may not start reliably.

**`dfu: true`** — enables USB DFU mode (flash without pressing hardware buttons).

---

## deep_sleep (added 2026-07-09, for sleep-current measurement)

`deep_sleep: run_duration: 5s / sleep_duration: 30s` added to the yaml — short cycle specifically so a multimeter/ammeter in series with the battery can catch the current drop during the sleep phase. `zigbee: sleepy` deliberately left `false` for this test (flipping it to `true` is a separate, riskier step per "sleepy: true breaks initial pairing" above — not needed just to observe sleep current).

**Note:** `nrf52: sleep_mode: system_off_ram_retention` (mentioned in some third-party ESPHome/nRF52 write-ups as the key to reaching µA-level sleep current) **does not exist** in the installed ESPHome version's `nrf52` component schema (checked `esphome/components/nrf52/__init__.py` directly — no such key, no `hardware_watchdog` option either). Don't re-add it without re-verifying against the actual installed component source first.

## Current Working Config (4 sensors + battery + deep_sleep, confirmed compiling 2026-07-09)

```yaml
esphome:
  name: "flower-monitor"
  friendly_name: "Flower Monitor"

logger:
  level: DEBUG

nrf52:
  board: adafruit_itsybitsy_nrf52840
  dcdc: false
  dfu: true

zigbee:
  sleepy: false
  wipe_on_boot: false

deep_sleep:
  run_duration: 5s
  sleep_duration: 30s

sensor:
  - platform: adc
    pin: P0.02
    name: "Влажность_почвы_1"
    icon: "mdi:water-percent"
    update_interval: 60s
    id: flower_1
  - platform: adc
    pin: P0.03
    name: "Влажность_почвы_2"
    icon: "mdi:water-percent"
    update_interval: 60s
    id: flower_2
  - platform: adc
    pin: P0.04
    name: "Влажность_почвы_3"
    icon: "mdi:water-percent"
    update_interval: 60s
    id: flower_3
  - platform: adc
    pin: P0.05
    name: "Влажность_почвы_4"
    icon: "mdi:water-percent"
    update_interval: 60s
    id: flower_4
  - platform: adc
    pin: P0.31
    name: "Батарея_напряжение"
    icon: "mdi:battery"
    unit_of_measurement: "V"
    update_interval: 60s
    id: battery_voltage
    filters:
      # raw = (Vbat/2) / Vref, divider 470k+470k, Vref assumed 3.6V (nRF52 SAADC default gain 1/6) — не подтверждено, откалибровать по мультиметру
      - multiply: 7.2
  - platform: template
    name: "Батарея_процент"
    icon: "mdi:battery-percent"
    unit_of_measurement: "%"
    update_interval: 60s
    id: battery_percent
    lambda: |-
      float v = id(battery_voltage).state;
      float pct = (v - 3.0f) / (4.2f - 3.0f) * 100.0f;
      if (pct < 0.0f) pct = 0.0f;
      if (pct > 100.0f) pct = 100.0f;
      return pct;
```
