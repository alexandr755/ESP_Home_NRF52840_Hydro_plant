import * as m from 'zigbee-herdsman-converters/lib/modernExtend';

export default {
    zigbeeModel: ['flower-monitor'],
    model: 'flower-monitor',
    vendor: 'esphome',
    description: 'ItsyBitsy NRF52840 4x capacitive soil moisture monitor',
    endpoint: (device) => {
        return {flower_1: 1, flower_2: 2, flower_3: 3, flower_4: 4};
    },
    extend: [m.numeric({
        name: 'humidity',
        label: 'Soil moisture',
        endpointNames: ['flower_1', 'flower_2', 'flower_3', 'flower_4'],
        cluster: 'genAnalogInput',
        attribute: 'presentValue',
        reporting: {min: 'MIN', max: 'MAX', change: 0.01},
        description: 'Soil moisture, scaled from raw ADC ratio (0-1) to percent',
        access: 'STATE_GET',
        unit: '%',
        scale: 0.01,
    })],
};
