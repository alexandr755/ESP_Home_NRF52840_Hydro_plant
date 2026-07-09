**Board:** SuperMini NRF52840 (ProMicro-form-factor clone board, chip: nRF52840-QIAA — not a genuine Adafruit/Nordic dev board)
**ESPHome version:** 2026.6.4

Confirming this on different hardware than the original report, and I think I found the actual mechanism plus a working workaround.

## Root cause

With `deep_sleep: sleep_duration: 20min` (or any explicit duration) set, `DeepSleepComponent::deep_sleep_()` in `deep_sleep_zephyr.cpp` takes this branch **regardless of whether `USE_ZIGBEE` is defined**:

```cpp
if (this->sleep_duration_.has_value()) {
  esphome::internal::wakeable_delay(static_cast<uint32_t>(*this->sleep_duration_ / 1000));
}
```

`sys_poweroff()` is never called here — only in the `else` branch (no `sleep_duration` set), and even there it's compiled out under `USE_ZIGBEE`. So the ~7mA plateau isn't a missed `sys_poweroff()` call in the explicit-`sleep_duration` case; `wakeable_delay()` is a plain Zephyr semaphore wait (`k_sem_take`) that lets the idle thread run WFI, but does nothing to the 802.15.4 radio. With Zigbee compiled in, the radio + ZBOSS stack simply stays powered/RX-on for the whole `wakeable_delay()`, which lines up with ~7mA being close to the nRF52840's documented radio-RX current.

I confirmed this by building an otherwise-identical firmware with the entire `zigbee:` block removed (same `deep_sleep`/`dcdc`/`logger` settings) — idle current dropped from ~7mA to **~14µA** (~500x), proving the SoC/Zephyr stack itself reaches µA-range sleep fine; it's specifically the radio staying active under Zigbee.

Worth noting for anyone tempted to chase `sys_poweroff()` as the fix: **it wouldn't work for a timer-woken sleepy end device anyway** — nRF52840 System OFF has no RTC/timer wake source, only external GPIO/LPCOMP/NFC/VBUS/reset. So the fix has to keep the CPU in a wakeable-by-timer idle state and instead explicitly put the *radio* to sleep, not the whole SoC.

## Workaround that worked for me

Patched `deep_sleep_zephyr.cpp` to explicitly sleep/wake the 802.15.4 radio around the delay, when `USE_ZIGBEE` is defined:

```cpp
#ifdef USE_ZIGBEE
extern "C" {
#include <nrf_802154.h>
}
#endif
...
void DeepSleepComponent::deep_sleep_() {
  if (this->sleep_duration_.has_value()) {
#ifdef USE_ZIGBEE
    nrf_802154_sleep();
#endif
    esphome::internal::wakeable_delay(static_cast<uint32_t>(*this->sleep_duration_ / 1000));
#ifdef USE_ZIGBEE
    nrf_802154_receive();
#endif
  } else {
    ...
  }
  ...
}
```

This bypasses ZBOSS's own radio ownership for just the sleep window, so I was cautious about it — main risk I expected was the ZHA coordinator aging the device out of its neighbor table and forcing a full rejoin every wake cycle.

**Tested and it held up:**
- Idle current with the patch: **~14µA**, matching the no-zigbee baseline — confirmed clean on a short interval (`sleep_duration: 20s`) with a visible 14µA→(active)→14µA cycle on an ammeter.
- Ran a longer soak test at production-length `sleep_duration: 30min`. Checked the device in Home Assistant/ZHA across several cycles: sensors report fresh values every cycle, **LQI stayed at max (255), RSSI unchanged (-35dBm)**, and the device's Zigbee activity log showed no repeated Interview/join events — it resumes and reports normally each wake, no rejoin regression observed so far.

I'd call this a promising workaround rather than a certain general fix — I've only run it on one board/network for a limited time, and directly driving `nrf_802154_*` underneath ZBOSS instead of going through its own sleep/poll APIs feels like it's fighting the stack's intended ownership model rather than cooperating with it, even though it's worked cleanly in my testing so far. Happy to share the full yaml/patch diff or test further if it's useful for narrowing down a proper fix.
