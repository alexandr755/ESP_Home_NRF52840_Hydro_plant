**Board:** SuperMini NRF52840 (ProMicro-form-factor clone board, chip: nRF52840-QIAA — not a genuine Adafruit/Nordic dev board)
**ESPHome version:** 2026.6.4

Confirming this on different hardware than the original report — same symptom, and I isolated it further.

With `zigbee:` active (`sleepy: true`, `power_source: BATTERY`, `wipe_on_boot: false`), `deep_sleep` (`run_duration: 10s`, `sleep_duration: 20min`), `nrf52.dcdc: true`, and `logger` fully disabled (`level: NONE`, `baud_rate: 0`), measured battery current with an ammeter in series:

- Active (during `run_duration`): ~10mA
- Idle/"asleep" plateau: **~7mA, flat, never drops further** — matches this issue and #13926 almost exactly

To isolate the cause, I built and flashed an otherwise-identical firmware with the entire `zigbee:` block commented out (no Zigbee component at all). Same `deep_sleep`/`dcdc`/`logger` settings, only the sensors and deep_sleep left active.

- Idle/"asleep" plateau without `zigbee:`: **~14µA** — a ~500x drop

This points pretty clearly at the `zigbee` component (radio and/or its associated timer) not being fully released/powered down before `deep_sleep` calls `sys_poweroff()` on nRF52/Zephyr — the chip itself is clearly capable of µA-range sleep (proven by the no-zigbee test), so the ~7mA floor with zigbee enabled looks like a software issue in the zigbee/deep_sleep interaction rather than a hardware limitation.

Happy to share the full yaml or test a patch if it'd help narrow this down.
