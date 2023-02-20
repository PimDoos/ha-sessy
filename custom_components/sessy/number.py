"""Number to read data from Sessy"""
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
from homeassistant.components.number import NumberEntity, NumberDeviceClass
from homeassistant.core import HomeAssistant

from sessypy.const import SessyApiCommand, SessySystemState
from sessypy.devices import SessyBattery, SessyDevice, SessyP1Meter


from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, SESSY_DEVICE
from .util import add_cache_command, enum_to_options_list, friendly_status_string, trigger_cache_update, unit_interval_to_percentage
from .sessyentity import SessyEntity

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    """Set up the Sessy numbers"""

    device = hass.data[DOMAIN][config_entry.entry_id][SESSY_DEVICE]
    numbers = []

    if isinstance(device, SessyBattery):
        await add_cache_command(hass, config_entry, SessyApiCommand.POWER_STATUS, DEFAULT_SCAN_INTERVAL)
        numbers.append(
            SessyNumber(hass, config_entry, "Power Setpoint",
                        SessyApiCommand.POWER_STATUS, "sessy.power_setpoint",
                        SessyApiCommand.POWER_SETPOINT, "setpoint",
                        NumberDeviceClass.POWER, POWER_WATT, -2200, 1700)
        )
    async_add_entities(numbers)
    
class SessyNumber(SessyEntity, NumberEntity):
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, name: str,
                 cache_command: SessyApiCommand, cache_key,
                 action_command: SessyApiCommand, action_key: SessyApiCommand,
                 device_class: NumberDeviceClass = None, unit_of_measurement = None,
                 min_value: float = None, max_value: float = None, transform_function: function = None):
        
        super().__init__(hass=hass, config_entry=config_entry, name=name, 
                       cache_command=cache_command, cache_key=cache_key, 
                       transform_function=transform_function)


        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        
        self.action_command = action_command
        self.action_key = action_key
    
    def update_from_cache(self):
        self._attr_available = self.cache_value != None
        self._attr_native_value = self.cache_value
        
    async def async_set_native_value(self, value: float):
        device: SessyDevice = self.hass.data[DOMAIN][self.config_entry.entry_id][SESSY_DEVICE]
        
        await device.api.post(self.action_command, {self.action_key: int(value)})
        await trigger_cache_update(self.hass, self.config_entry, self.cache_command)