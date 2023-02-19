"""Sensor to read vehicle data from Sessy"""
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
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from sessypy.const import SessyApiCommand, SessyPowerStrategy, SessySystemState
from sessypy.devices import SessyBattery, SessyDevice, SessyP1Meter


from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, SERIAL_NUMBER, SESSY_CACHE, SESSY_DEVICE, SESSY_DEVICE_INFO, UPDATE_TOPIC
from .util import add_cache_command, enum_to_options_list, friendly_status_string, unit_interval_to_percentage
from .sessyentity import SessyEntity

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    """Set up the Sessy sensors"""

    device = hass.data[DOMAIN][config_entry.entry_id][SESSY_DEVICE]
    sensors = []

    if isinstance(device, SessyBattery):
        await add_cache_command(hass, config_entry, SessyApiCommand.NETWORK_STATUS, DEFAULT_SCAN_INTERVAL)
        sensors.append(
            SessySensor(hass, config_entry, "WiFi RSSI",
                        SessyApiCommand.NETWORK_STATUS, "wifi_sta.rssi",
                        SensorDeviceClass.SIGNAL_STRENGTH, SensorStateClass.MEASUREMENT, SIGNAL_STRENGTH_DECIBELS_MILLIWATT)
        )
        await add_cache_command(hass, config_entry, SessyApiCommand.POWER_STATUS, DEFAULT_SCAN_INTERVAL)
        sensors.append(
            SessySensor(hass, config_entry, "System State",
                        SessyApiCommand.POWER_STATUS, "sessy.system_state",
                        SensorDeviceClass.ENUM,
                        transform_function=friendly_status_string, options = enum_to_options_list(SessySystemState))
        )
        sensors.append(
            SessySensor(hass, config_entry, "State of Charge",
                        SessyApiCommand.POWER_STATUS, "sessy.state_of_charge",
                        SensorDeviceClass.BATTERY, SensorStateClass.MEASUREMENT, PERCENTAGE,
                        transform_function=unit_interval_to_percentage)
        )
        sensors.append(
            SessySensor(hass, config_entry, "Power",
                        SessyApiCommand.POWER_STATUS, "sessy.power",
                        SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, POWER_WATT)
        )
        sensors.append(
            SessySensor(hass, config_entry, "Power Setpoint",
                        SessyApiCommand.POWER_STATUS, "sessy.power_setpoint",
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
        await add_cache_command(hass, config_entry, SessyApiCommand.P1_STATUS, DEFAULT_SCAN_INTERVAL)
        sensors.append(
            SessySensor(hass, config_entry, "P1 Power",
                        SessyApiCommand.P1_STATUS, "net_power_delivered",
                        SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, POWER_KILO_WATT)
        )

    async_add_entities(sensors)


    
class SessySensor(SessyEntity, SensorEntity):
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, name: str,
                 cache_command: SessyApiCommand, cache_key,
                 device_class: SensorDeviceClass = None, state_class: SensorStateClass = None, unit_of_measurement = None,
                 options = None, transform_function: function = None):
        
        super().__init__(hass=hass, config_entry=config_entry, name=name, 
                       cache_command=cache_command, cache_key=cache_key, 
                       transform_function=transform_function)

        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_unit_of_measurement = unit_of_measurement
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_options = options

    # async def async_added_to_hass(self):
    #     @callback
    #     def update():
    #         self.cache = self.hass.data[DOMAIN][self.config_entry.entry_id][SESSY_CACHE][self.cache_command]
    #         self.async_write_ha_state()

    #     await super().async_added_to_hass()
    #     self.update_topic_listener = async_dispatcher_connect(
    #         self.hass, self.update_topic, update
    #     )
    #     self.async_on_remove(self.update_topic_listener)

    # @property
    # def should_poll(self) -> bool:
    #     return False
    
    # @property
    # def state(self):
    #     value = self.get_cache_value(self.cache_key)
    #     if self.transform_function:
    #         return self.transform_function(value)
    #     else:
    #         return self.get_cache_value(self.cache_key)
    
    # @property
    # def available(self):
    #     return self.get_cache_value(self.cache_key) != None
    
    # def get_cache_value(self, key):
    #     if self.cache == None:
    #         return None

    #     value = self.cache

    #     if len(value) == 0:
    #         return None
    #     else:
    #         node: str
    #         for node in key.split("."):
    #             if node.isdigit():
    #                 node = int(node)
    #             if value == None:
    #                 return None
    #             elif node in value:
    #                 value = value[node]
    #                 continue
    #             else:
    #                 value = None
    #     return value