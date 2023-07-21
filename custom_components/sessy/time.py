"""Time entities to control Sessy"""
from __future__ import annotations
from datetime import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.components.time import TimeEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from sessypy.const import SessyApiCommand
from sessypy.devices import SessyBattery, SessyDevice
from sessypy.util import SessyConnectionException, SessyNotSupportedException


from .const import DOMAIN, SESSY_DEVICE, DEFAULT_SCAN_INTERVAL
from .util import add_cache_command, start_time_from_string, stop_time_from_string, time_from_string, trigger_cache_update
from .sessyentity import SessyEntity

import logging
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    """Set up the Sessy time entities"""

    device = hass.data[DOMAIN][config_entry.entry_id][SESSY_DEVICE]
    times = []

    if isinstance(device, SessyBattery):
        await add_cache_command(hass, config_entry, SessyApiCommand.SYSTEM_SETTINGS, DEFAULT_SCAN_INTERVAL)
        
        async def partial_update_enabled_time(start_time: time = None, stop_time: time = None) -> str:
            settings: dict = await device.get_system_settings()
            settings_enabled_time = settings.get("enabled_time").split("-")

            if not start_time:
                start_time = time_from_string(settings_enabled_time[0])

            if not stop_time:
                stop_time = time_from_string(settings_enabled_time[1])

            settings_enabled_time = f"{start_time.strftime('%H:%M')}-{stop_time.strftime('%H:%M')}"
            settings["enabled_time"] = settings_enabled_time
            return settings
        
        async def update_start_time(key, value: time):
            return await partial_update_enabled_time(start_time = value)
        
        async def update_stop_time(key, value: time):
            return await partial_update_enabled_time(stop_time = value)
        
        times.append(
            SessyTime(hass, config_entry, "Start Time",
                        SessyApiCommand.SYSTEM_SETTINGS, "enabled_time",
                        SessyApiCommand.SYSTEM_SETTINGS, "enabled_time",
                        entity_category=EntityCategory.CONFIG,
                        action_function=update_start_time,
                        transform_function=start_time_from_string)
            
        ),
        times.append(
            SessyTime(hass, config_entry, "Stop Time",
                        SessyApiCommand.SYSTEM_SETTINGS, "enabled_time",
                        SessyApiCommand.SYSTEM_SETTINGS, "enabled_time",
                        entity_category=EntityCategory.CONFIG,
                        action_function=update_stop_time,
                        transform_function=stop_time_from_string)
            
        )

    async_add_entities(times)
    
class SessyTime(SessyEntity, TimeEntity):
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, name: str,
                 cache_command: SessyApiCommand, cache_key,
                 action_command: SessyApiCommand, action_key: SessyApiCommand,
                 entity_category: EntityCategory = None,
                 transform_function: function = None, action_function: function = None):
        
        super().__init__(hass=hass, config_entry=config_entry, name=name, 
                       cache_command=cache_command, cache_key=cache_key, 
                       transform_function=transform_function)

        self._attr_entity_category = entity_category
        
        self.action_command = action_command
        self.action_key = action_key
        self.action_function: function = action_function
    
    def update_from_cache(self):
        self._attr_available = self.cache_value != None
        self._attr_native_value = self.cache_value
        
    async def async_set_value(self, value: time):
        device: SessyDevice = self.hass.data[DOMAIN][self.config_entry.entry_id][SESSY_DEVICE]
        try:
            if not self.action_function:
                payload = {self.action_key: str(value)}
            else:
                payload = await self.action_function(self.action_key, value)
                
            await device.api.post(self.action_command, payload)
        except SessyNotSupportedException:
            _LOGGER.error(f"Setting value for {self.name} failed: Not supported by device")
            
        except SessyConnectionException:
            _LOGGER.error(f"Setting value for {self.name} failed: Connection error")

        except Exception as e:
            _LOGGER.error(f"Setting value for {self.name} failed: {e.__class__}")
            
        await trigger_cache_update(self.hass, self.config_entry, self.cache_command)
