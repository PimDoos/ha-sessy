"""Button entities to control Sessy"""
from __future__ import annotations
from enum import Enum

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.button import ButtonEntity, ButtonDeviceClass
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory

from sessypy.const import SessyApiCommand
from sessypy.devices import SessyDevice
from sessypy.util import SessyConnectionException, SessyNotSupportedException


from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, SESSY_DEVICE
from .util import add_cache_command
from .sessyentity import SessyEntity

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    """Set up the Sessy buttons"""

    device: SessyDevice = hass.data[DOMAIN][config_entry.entry_id][SESSY_DEVICE]
    buttons = []

    await add_cache_command(hass, config_entry, SessyApiCommand.SYSTEM_INFO, DEFAULT_SCAN_INTERVAL)
    buttons.append(
        SessyButton(hass, config_entry, "Dongle Restart",
                    SessyApiCommand.SYSTEM_INFO, 'status', device.restart,
                    device_class=ButtonDeviceClass.RESTART, entity_category=EntityCategory.DIAGNOSTIC
                    )
    )

    async_add_entities(buttons)
    
class SessyButton(SessyEntity, ButtonEntity):
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, name: str,
                 cache_command: SessyApiCommand, cache_key: str, action_function: function,
                 device_class: ButtonDeviceClass = None, entity_category: EntityCategory = None, 
                 transform_function: function = None, translation_key: str = None):
        
        super().__init__(hass=hass, config_entry=config_entry, name=name, 
                       cache_command=cache_command, cache_key=cache_key, 
                       transform_function=transform_function, translation_key=translation_key)
        
        self.action_function = action_function
        self._attr_device_class = device_class
        self._attr_entity_category = entity_category
        
    def update_from_cache(self):
        self._attr_available = self.cache_value != None
        
    async def async_press(self):
        try:
            await self.action_function()
        except SessyNotSupportedException as e:
            raise HomeAssistantError(f"Sending command for {self.name} failed: Not supported by device") from e
            
        except SessyConnectionException as e:
            raise HomeAssistantError(f"Sending command for {self.name} failed: Connection error") from e

        except Exception as e:
            raise HomeAssistantError(f"Sending command for {self.name} failed: {e.__class__}") from e