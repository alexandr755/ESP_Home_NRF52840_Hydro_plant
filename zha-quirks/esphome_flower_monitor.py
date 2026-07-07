from zigpy.quirks.v2 import QuirkBuilder, SensorDeviceClass, SensorStateClass
from zigpy.zcl.clusters.general import AnalogInput

MANUFACTURER = "esphome"
MODEL = "flower-monitor"

(
    QuirkBuilder(MANUFACTURER, MODEL)
    .sensor(
        "present_value",
        AnalogInput.cluster_id,
        endpoint_id=1,
        divisor=1,
        multiplier=100,
        unit="%",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        translation_key="soil_moisture_1",
        fallback_name="Soil moisture 1",
    )
    .sensor(
        "present_value",
        AnalogInput.cluster_id,
        endpoint_id=2,
        divisor=1,
        multiplier=100,
        unit="%",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        translation_key="soil_moisture_2",
        fallback_name="Soil moisture 2",
    )
    .sensor(
        "present_value",
        AnalogInput.cluster_id,
        endpoint_id=3,
        divisor=1,
        multiplier=100,
        unit="%",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        translation_key="soil_moisture_3",
        fallback_name="Soil moisture 3",
    )
    .sensor(
        "present_value",
        AnalogInput.cluster_id,
        endpoint_id=4,
        divisor=1,
        multiplier=100,
        unit="%",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        translation_key="soil_moisture_4",
        fallback_name="Soil moisture 4",
    )
    .add_to_registry()
)
