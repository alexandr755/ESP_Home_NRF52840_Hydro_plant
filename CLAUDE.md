# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ESPHome firmware for a 4-plant soil moisture monitor (one board, 4 independent sensors). Target hardware: **Adafruit ItsyBitsy NRF52840**, communicating over **Zigbee** (End Device), integrated with **Home Assistant via Zigbee2MQTT**.

Sensor: 4x capacitive soil moisture v1.2 (analog output), powered via GPIO switch to save battery (planned, shared switch — not yet wired).
Power: 18650 Li-ion battery via TP4056 charging module (planned).

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

## Pin Map (Adafruit ItsyBitsy NRF52840)

Analog-capable pins on this board (Arduino alias → GPIO → SAADC channel), from the official variant files: A4=P0.02=AIN0, A5=P0.03=AIN1, A0=P0.04=AIN2, A6/D10=P0.05=AIN3, A2=P0.28=AIN4, A1=P0.30=AIN6, A3=P0.31=AIN7. Max 8 Zigbee endpoints on nrf52 (`CONF_MAX_EP_NUMBER = 8`).

| ESPHome ID | Physical pin | Role |
|---|---|---|
| `power_pin_pull` | `P0.13` | Bus power pull (clone board fix) |
| `sensor_vcc_power` | `P0.08` | Sensor VCC enable switch (planned, shared across all 4 sensors — not yet wired) |
| `flower_1` (ADC) | `P0.02` (AIN0 / A4) | Soil moisture sensor 1 |
| `flower_2` (ADC) | `P0.03` (AIN1 / A5) | Soil moisture sensor 2 |
| `flower_3` (ADC) | `P0.04` (AIN2 / A0) | Soil moisture sensor 3 |
| `flower_4` (ADC) | `P0.05` (AIN3 / A6/D10) | Soil moisture sensor 4 |
| battery monitor | `P0.28` (AIN4 / A2) reserved | Voltage divider for battery % (not yet wired) |

Free/spare after the above: `P0.30` (AIN6/A1), `P0.31` (AIN7/A3).

**`dcdc: false`** — must stay off; ItsyBitsy NRF52840 has no external inductor for the DC/DC converter. Without this flag the board may not start reliably.

**`dfu: true`** — enables USB DFU mode (flash without pressing hardware buttons).

---

## Current Working Config (4 sensors, confirmed compiling 2026-07-06)

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
  wipe_on_boot: once

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
```
