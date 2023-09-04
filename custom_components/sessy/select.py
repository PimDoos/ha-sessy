"""Select entities to control Sessy"""
from __future__ import annotations
from enum import Enum

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.select import SelectEntity
from homeassistant.exceptions import HomeAssistantError

from sessypy.const import SessyApiCommand, SessyPowerStrategy
from sessypy.devices import SessyBattery, SessyDevice
from sessypy.util import SessyConnectionException, SessyNotSupportedException


from .const import DOMAIN, SESSY_DEVICE
from .util import  enum_to_options_list, trigger_cache_update, status_string_power_strategy
from .sessyentity import SessyEntity

import logging
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    """Set up the Sessy selects"""

    device = hass.data[DOMAIN][config_entry.entry_id][SESSY_DEVICE]
    selects = []

    if isinstance(device, SessyBattery):
        selects.append(
            SessySelect(hass, config_entry, "Power Strategy",
                        SessyApiCommand.POWER_STRATEGY,"strategy",
                        options=SessyPowerStrategy, translation_key = "battery_strategy", transform_function=status_string_power_strategy)
        )

    async_add_entities(selects)
    
class SessySelect(SessyEntity, SelectEntity):
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, name: str,
                 cache_command: SessyApiCommand, cache_key,
                 options: Enum, transform_function: function = None, translation_key: str = None):
        
        super().__init__(hass=hass, config_entry=config_entry, name=name, 
                       cache_command=cache_command, cache_key=cache_key, 
                       transform_function=transform_function, translation_key=translation_key)
        
        self.real_options = enum_to_options_list(options)
        self._attr_options = enum_to_options_list(options, transform_function)
        
    def update_from_cache(self):
        self._attr_available = self.cache_value != None
        self._attr_current_option = self.cache_value
        
    async def async_select_option(self, option: str) -> None:
        device: SessyDevice = self.hass.data[DOMAIN][self.config_entry.entry_id][SESSY_DEVICE]

        try:
            if self.transform_function:
                option_index = self._attr_options.index(option)
                option = self.real_options[option_index]

            await device.api.post(self.cache_command, {self.cache_key: option})
        except SessyNotSupportedException as e:
            raise HomeAssistantError(f"Setting value for {self.name} failed: Not supported by device") from e
            
        except SessyConnectionException as e:
            raise HomeAssistantError(f"Setting value for {self.name} failed: Connection error") from e

        except Exception as e:
            raise HomeAssistantError(f"Setting value for {self.name} failed: {e.__class__}") from e

        await trigger_cache_update(self.hass, self.config_entry, self.cache_command)
