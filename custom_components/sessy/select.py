"""Select entities to control Sessy"""
from __future__ import annotations
from enum import Enum

from homeassistant.core import HomeAssistant
from homeassistant.components.select import SelectEntity
from homeassistant.exceptions import HomeAssistantError

from sessypy.const import SessyPowerStrategy
from sessypy.devices import SessyBattery
from sessypy.util import SessyConnectionException, SessyNotSupportedException

from typing import Callable, Optional

from .coordinator import SessyCoordinator, SessyCoordinatorEntity
from .models import SessyConfigEntry
from .util import  enum_to_options_list, status_string_power_strategy

import logging
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: SessyConfigEntry, async_add_entities):
    """Set up the Sessy selects"""

    device = config_entry.runtime_data.device
    coordinators = config_entry.runtime_data.coordinators
    selects = []

    if isinstance(device, SessyBattery):
        selects.append(
            SessySelectEntity(hass, config_entry, "Power Strategy",
                        coordinators[device.get_power_strategy],"strategy", action_function=device.set_power_strategy,
                        options=SessyPowerStrategy, translation_key = "battery_strategy", transform_function=status_string_power_strategy)
        )

    async_add_entities(selects)
    
class SessySelectEntity(SessyCoordinatorEntity, SelectEntity):
    def __init__(self, hass: HomeAssistant, config_entry: SessyConfigEntry, name: str,
                 coordinator: SessyCoordinator, data_key, action_function: Callable,
                 options: Enum, transform_function: Optional[Callable],translation_key: str = None):
        
        super().__init__(hass=hass, config_entry=config_entry, name=name, 
                       coordinator=coordinator, data_key=data_key, 
                       transform_function=transform_function, translation_key=translation_key)
        self.action_function = action_function
        self.real_options = enum_to_options_list(options)
        self._attr_options = enum_to_options_list(options, transform_function)
        self._attr_current_option = None

    def update_from_cache(self):
        self._attr_available = self.cache_value is not None
        self._attr_current_option = self.cache_value
        
    async def async_select_option(self, option: str) -> None:
        try:
            if self.transform_function:
                option_index = self._attr_options.index(option)
                option = self.real_options[option_index]

            await self.action_function(option)
        except SessyNotSupportedException as e:
            raise HomeAssistantError(f"Setting value for {self.name} failed: Not supported by device") from e
            
        except SessyConnectionException as e:
            raise HomeAssistantError(f"Setting value for {self.name} failed: Connection error") from e

        except Exception as e:
            raise HomeAssistantError(f"Setting value for {self.name} failed: {e.__class__}") from e

        await self.coordinator.async_refresh()
