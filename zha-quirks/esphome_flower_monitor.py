from zigpy.quirks.v2 import (
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,
    SensorStateClass,
)
from zigpy.zcl.clusters.general import AnalogInput

MANUFACTURER = "esphome"
MODEL = "flower-monitor"

# Критично для энергопотребления (найдено 2026-07-19): ZHA'шный дефолтный Configure Reporting
# (установленный на устройство при Reconfigure Device) заставляет ZBOSS самостоятельно слать
# периодические репорты по таймеру. Таймер срабатывает посреди окна deep_sleep, будит радио,
# и из-за rx_on_when_idle=true оно остаётся в приёме до конца окна (~9.6мА вместо ~14мкА).
# max_interval=0 по ZCL-спецификации = "периодических репортов нет, только по изменению" —
# а изменения атрибутов происходят только когда ESPHome пишет их в активном окне (и сам
# форсирует отправку), так что репорты по построению не попадают в окно сна.
# min_interval=0 — слать сразу; reportable_change=0 — любое изменение значимо.
ON_CHANGE_ONLY = ReportingConfig(min_interval=0, max_interval=0, reportable_change=0)

(
    QuirkBuilder(MANUFACTURER, MODEL)
    .sensor(
        # Calibrated 2026-07-18 (real capacitive sensors wired to endpoints 1-4, same calibration
        # reused across all 4 — same sensor batch). ESPHome now applies calibrate_linear itself and
        # already sends 0-100, hence multiplier=1 (not 100) on all four of these.
        "present_value",
        AnalogInput.cluster_id,
        endpoint_id=1,
        divisor=1,
        multiplier=1,
        unit="%",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        translation_key="soil_moisture_1",
        fallback_name="Soil moisture 1",
        reporting_config=ON_CHANGE_ONLY,
    )
    .sensor(
        "present_value",
        AnalogInput.cluster_id,
        endpoint_id=2,
        divisor=1,
        multiplier=1,
        unit="%",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        translation_key="soil_moisture_2",
        fallback_name="Soil moisture 2",
        reporting_config=ON_CHANGE_ONLY,
    )
    .sensor(
        "present_value",
        AnalogInput.cluster_id,
        endpoint_id=3,
        divisor=1,
        multiplier=1,
        unit="%",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        translation_key="soil_moisture_3",
        fallback_name="Soil moisture 3",
        reporting_config=ON_CHANGE_ONLY,
    )
    .sensor(
        "present_value",
        AnalogInput.cluster_id,
        endpoint_id=4,
        divisor=1,
        multiplier=1,
        unit="%",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        translation_key="soil_moisture_4",
        fallback_name="Soil moisture 4",
        reporting_config=ON_CHANGE_ONLY,
    )
    .sensor(
        # ESPHome already applies the divider-ratio multiply filter before sending,
        # so present_value here is already real volts — no extra scaling needed.
        "present_value",
        AnalogInput.cluster_id,
        endpoint_id=5,
        divisor=1,
        multiplier=1,
        unit="V",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        translation_key="battery_voltage",
        fallback_name="Battery voltage",
        reporting_config=ON_CHANGE_ONLY,
    )
    .sensor(
        # ESPHome's template sensor lambda already outputs 0-100, sent as-is.
        "present_value",
        AnalogInput.cluster_id,
        endpoint_id=6,
        divisor=1,
        multiplier=1,
        unit="%",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        translation_key="battery_percent",
        fallback_name="Battery percent",
        reporting_config=ON_CHANGE_ONLY,
    )
    .add_to_registry()
)
