"""Sensor to read data from Sessy"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    POWER_KILO_WATT,
    POWER_WATT,
    ENERGY_KILO_WATT_HOUR,
    PERCENTAGE,
    ELECTRIC_POTENTIAL_MILLIVOLT,
    ELECTRIC_CURRENT_AMPERE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT
)
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.core import HomeAssistant

from sessypy.const import SessyApiCommand, SessySystemState
from sessypy.devices import SessyBattery, SessyDevice, SessyP1Meter


from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, SESSY_DEVICE, SCAN_INTERVAL_POWER
from .util import add_cache_command, enum_to_options_list, friendly_status_string, unit_interval_to_percentage
from .sessyentity import SessyEntity

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    """Set up the Sessy sensors"""

    device = hass.data[DOMAIN][config_entry.entry_id][SESSY_DEVICE]
    sensors = []

    await add_cache_command(hass, config_entry, SessyApiCommand.NETWORK_STATUS)
    sensors.append(
        SessySensor(hass, config_entry, "WiFi RSSI",
                    SessyApiCommand.NETWORK_STATUS, "wifi_sta.rssi",
                    SensorDeviceClass.SIGNAL_STRENGTH, SensorStateClass.MEASUREMENT, SIGNAL_STRENGTH_DECIBELS_MILLIWATT)
    )

    if isinstance(device, SessyBattery):
        await add_cache_command(hass, config_entry, SessyApiCommand.POWER_STATUS, SCAN_INTERVAL_POWER)
        sensors.append(
            SessySensor(hass, config_entry, "System State",
                        SessyApiCommand.POWER_STATUS, "sessy.system_state",
                        SensorDeviceClass.ENUM,
                        transform_function=friendly_status_string, options = enum_to_options_list(SessySystemState, friendly_status_string))
        )
        sensors.append(
            SessySensor(hass, config_entry, "State of Charge",
                        SessyApiCommand.POWER_STATUS, "sessy.state_of_charge",
                        SensorDeviceClass.BATTERY, SensorStateClass.MEASUREMENT, PERCENTAGE,
                        transform_function=unit_interval_to_percentage, precision = 1)
        )
        sensors.append(
            SessySensor(hass, config_entry, "Power",
                        SessyApiCommand.POWER_STATUS, "sessy.power",
                        SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, POWER_WATT)
        )
        for phase_id in range(1,4): 
            sensors.append(
                SessySensor(hass, config_entry, f"Renewable Energy Phase { phase_id } Voltage",
                            SessyApiCommand.POWER_STATUS, f"renewable_energy_phase{ phase_id }.voltage_rms",
                            SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, ELECTRIC_POTENTIAL_MILLIVOLT)
            )
            sensors.append(
                SessySensor(hass, config_entry, f"Renewable Energy Phase { phase_id } Current",
                            SessyApiCommand.POWER_STATUS, f"renewable_energy_phase{ phase_id }.current_rms",
                            SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, ELECTRIC_CURRENT_AMPERE)
            )
            sensors.append(
                SessySensor(hass, config_entry, f"Renewable Energy Phase { phase_id } Power",
                            SessyApiCommand.POWER_STATUS, f"renewable_energy_phase{ phase_id }.power",
                            SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, POWER_WATT)
            )


    elif isinstance(device, SessyP1Meter):
        await add_cache_command(hass, config_entry, SessyApiCommand.P1_STATUS, SCAN_INTERVAL_POWER)
        sensors.append(
            SessySensor(hass, config_entry, "P1 Power",
                        SessyApiCommand.P1_STATUS, "net_power_delivered",
                        SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, POWER_KILO_WATT, precision = 3)
        )

    async_add_entities(sensors)
    
class SessySensor(SessyEntity, SensorEntity):
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, name: str,
                 cache_command: SessyApiCommand, cache_key,
                 device_class: SensorDeviceClass = None, state_class: SensorStateClass = None, unit_of_measurement = None,
                 options = None, transform_function: function = None, precision: int = None):
        
        super().__init__(hass=hass, config_entry=config_entry, name=name, 
                       cache_command=cache_command, cache_key=cache_key, 
                       transform_function=transform_function)

        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_native_unit_of_measurement = unit_of_measurement

        # TODO move this to _attr_suggested_display_precision in 2022.3
        self._attr_native_precision = precision
        self._attr_options = options
    
    def update_from_cache(self):
        self._attr_available = self.cache_value != None
        self._attr_native_value = self.cache_value