import * as m from 'zigbee-herdsman-converters/lib/modernExtend';

export default {
    zigbeeModel: ['single-flower-monitor'],
    model: 'single-flower-monitor',
    vendor: 'esphome',
    description: 'ItsyBitsy NRF52840 capacitive soil moisture monitor',
    extend: [m.numeric({
        name: 'humidity',
        label: 'Soil moisture',
        cluster: 'genAnalogInput',
        attribute: 'presentValue',
        reporting: {min: 'MIN', max: 'MAX', change: 0.01},
        description: 'Soil moisture, scaled from raw ADC ratio (0-1) to percent',
        access: 'STATE_GET',
        unit: '%',
        scale: 0.01,
    })],
};
