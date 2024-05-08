"""Switch to read data from Sessy"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory

from sessypy.const import SessyApiCommand
from sessypy.devices import SessyBattery, SessyDevice, SessyMeter
from sessypy.util import SessyNotSupportedException, SessyConnectionException


from .const import DOMAIN, SESSY_DEVICE
from .util import get_cache_command, trigger_cache_update
from .sessyentity import SessyEntity

import logging
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    """Set up the Sessy switches"""

    device = hass.data[DOMAIN][config_entry.entry_id][SESSY_DEVICE]
    switches = []

    if isinstance(device, SessyBattery):

        async def partial_update_settings(key,value):
            settings: dict = await device.get_system_settings()
            settings[key] = value
            return settings
        
        # Firmware or hardware-revision specific settings
        try:
            settings: dict = get_cache_command(hass, config_entry, SessyApiCommand.SYSTEM_SETTINGS)
        
            # Eco mode controls (fw 1.6.8+)
            if settings.get("eco_nom_charge", None) != None:
                switches.append(
                    SessySwitch(hass, config_entry, "Eco NOM Charging Enabled",
                                SessyApiCommand.SYSTEM_SETTINGS, "eco_nom_charge",
                                SessyApiCommand.SYSTEM_SETTINGS, "eco_nom_charge",
                                entity_category=EntityCategory.CONFIG,
                                action_function=partial_update_settings)
                )
        except Exception as e:
            _LOGGER.warning(f"Error setting firmware specific settings: {e}")

    async_add_entities(switches)
    
class SessySwitch(SessyEntity, SwitchEntity):
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, name: str,
                 cache_command: SessyApiCommand, cache_key,
                 action_command: SessyApiCommand, action_key: SessyApiCommand,
                 device_class: SwitchDeviceClass = None, 
                 entity_category: EntityCategory = None,
                 transform_function: function = None, action_function: function = None):
        
        super().__init__(hass=hass, config_entry=config_entry, name=name, 
                       cache_command=cache_command, cache_key=cache_key, 
                       transform_function=transform_function)


        self._attr_device_class = device_class
        self._attr_entity_category = entity_category
        
        self.action_command = action_command
        self.action_key = action_key
        self.action_function: function = action_function
    
    def update_from_cache(self):
        self._attr_available = self.cache_value != None
        self._attr_is_on = self.cache_value
        

    async def async_turn_on(self):
        self._set_value(True)
            
    async def async_turn_off(self):
        self._set_value(False)
    
    async def _set_value(self, value: bool):
        device: SessyDevice = self.hass.data[DOMAIN][self.config_entry.entry_id][SESSY_DEVICE]
        try:
            if not self.action_function:
                payload = {self.action_key: value}
            else:
                payload = await self.action_function(self.action_key, value)
                
            await device.api.post(self.action_command, payload)
        except SessyNotSupportedException as e:
            raise HomeAssistantError(f"Setting value for {self.name} failed: Not supported by device") from e

        except SessyConnectionException as e:
            raise HomeAssistantError(f"Setting value for {self.name} failed: Connection error") from e

        except Exception as e:
            raise HomeAssistantError(f"Setting value for {self.name} failed: {e.__class__}") from e

        await trigger_cache_update(self.hass, self.config_entry, self.cache_command)
