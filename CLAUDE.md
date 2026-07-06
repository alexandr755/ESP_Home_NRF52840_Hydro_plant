# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ESPHome firmware for a single-plant soil moisture monitor. Target hardware: **Adafruit ItsyBitsy NRF52840**, communicating over **Zigbee** (End Device), integrated with **Home Assistant via Zigbee2MQTT**.

Sensor: capacitive soil moisture v1.2 (analog output), powered via GPIO switch to save battery.
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
~/esphome-projects/hydro-plant/.esphome/build/single-flower-monitor/.pioenvs/single-flower-monitor/
├── firmware.hex / firmware.elf
└── zephyr/{zephyr.hex, zephyr.bin, zephyr.uf2, merged.hex}
```

**Copy firmware back to Windows** (for flashing via UF2 drag-and-drop):
```powershell
wsl.exe -d Ubuntu-26.04 -- bash -lc "cp ~/esphome-projects/hydro-plant/.esphome/build/single-flower-monitor/.pioenvs/single-flower-monitor/zephyr/zephyr.uf2 /mnt/c/PlatformIO/Projects/ESP_Home_NRF52840_Hydro_plant/single-flower-monitor.uf2"
```

See `manual.md` for the full step-by-step workflow.

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

| ESPHome ID | Physical pin | Role |
|---|---|---|
| `power_pin_pull` | `P0.13` | Bus power pull (clone board fix) |
| `sensor_vcc_power` | `P0.08` | Sensor VCC enable switch |
| `flower_1` (ADC) | `P0.02` (AIN0) | Capacitive moisture sensor output |
| battery monitor | TBD free AIN | Voltage divider for battery % (not yet wired) |

**`dcdc: false`** — must stay off; ItsyBitsy NRF52840 has no external inductor for the DC/DC converter. Without this flag the board may not start reliably.

**`dfu: true`** — enables USB DFU mode (flash without pressing hardware buttons).

---

## Current Working Config (connectivity test, no physical sensor needed)

```yaml
esphome:
  name: "single-flower-monitor"
  friendly_name: "Monitor_flower1"

logger:
  level: DEBUG

nrf52:
  board: adafruit_itsybitsy_nrf52840
  dcdc: false
  dfu: true

zigbee:
  sleepy: false

sensor:
  - platform: adc
    pin: P0.02
    name: "Влажность_почвы"
    icon: "mdi:water-percent"
    update_interval: 60s
    id: flower_1
```
