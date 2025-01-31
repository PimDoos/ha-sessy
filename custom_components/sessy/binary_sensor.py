"""BinarySensor to read data from Sessy"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from sessypy.const import SessyApiCommand, SessySystemState
from sessypy.devices import SessyBattery

from .const import DOMAIN, SESSY_DEVICE
from .util import (enum_to_options_list, get_cache_command, status_string_system_state)
from .sessyentity import SessyEntity

import logging
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    """Set up the Sessy binary_sensors"""

    device = hass.data[DOMAIN][config_entry.entry_id][SESSY_DEVICE]
    binary_sensors = []
    
    if isinstance(device, SessyBattery):
        # Power Status
        try:
            power_status: dict = get_cache_command(hass, config_entry, SessyApiCommand.POWER_STATUS)

            if "strategy_overridden" in power_status.get("sessy", dict()):
                binary_sensors.append(
                    SessyBinarySensor(hass, config_entry, "Strategy Override",
                                SessyApiCommand.POWER_STATUS, "sessy.strategy_overridden",
                                BinarySensorDeviceClass.RUNNING, entity_category=EntityCategory.DIAGNOSTIC)
                )
            
        except Exception as e:
            _LOGGER.warning(f"Error setting up power status binary_sensors: {e}")

    async_add_entities(binary_sensors)

class SessyBinarySensor(SessyEntity, BinarySensorEntity):
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, name: str,
                 cache_command: SessyApiCommand, cache_key,
                 device_class: BinarySensorDeviceClass = None,
                 transform_function: function = None, 
                 entity_category: EntityCategory = None, enabled_default: bool = True):

        super().__init__(hass=hass, config_entry=config_entry, name=name,
                       cache_command=cache_command, cache_key=cache_key,
                       transform_function=transform_function)

        self._attr_device_class = device_class
        self._attr_entity_category = entity_category

        self._attr_entity_registry_enabled_default = enabled_default

    def update_from_cache(self):
        self._attr_available = self.cache_value != None
        self._attr_is_on = self.cache_value
