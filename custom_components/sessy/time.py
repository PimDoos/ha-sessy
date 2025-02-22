"""Time entities to control Sessy"""
from __future__ import annotations
from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory

from sessypy.devices import SessyBattery, SessyDevice
from sessypy.util import SessyConnectionException, SessyNotSupportedException

from .coordinator import SessyCoordinator, SessyCoordinatorEntity
from .models import SessyConfigEntry
from .util import start_time_from_string, stop_time_from_string, time_from_string

import logging
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: SessyConfigEntry, async_add_entities):
    """Set up the Sessy time entities"""

    device = config_entry.runtime_data.device
    coordinators = config_entry.runtime_data.coordinators
    time_entities = []

    if isinstance(device, SessyBattery):
        system_settings_coordinator: SessyCoordinator = coordinators[device.get_system_settings]

        async def partial_update_enabled_time(start_time: time = None, stop_time: time = None) -> str:
            settings: dict = system_settings_coordinator.raw_data
            settings_enabled_time = settings.get("enabled_time").split("-")

            if not start_time:
                start_time = time_from_string(settings_enabled_time[0])

            if not stop_time:
                stop_time = time_from_string(settings_enabled_time[1])

            settings_enabled_time = f"{start_time.strftime('%H:%M')}-{stop_time.strftime('%H:%M')}"
            return await device.set_system_setting("enabled_time", settings_enabled_time)
        
        async def update_start_time(value: time):
            return await partial_update_enabled_time(start_time = value)
        
        async def update_stop_time(value: time):
            return await partial_update_enabled_time(stop_time = value)
        
        time_entities.append(
            SessyTimeEntity(hass, config_entry, "Start Time",
                        system_settings_coordinator, "enabled_time",
                        update_start_time,
                        entity_category=EntityCategory.CONFIG,
                        transform_function=start_time_from_string)
            
        ),
        time_entities.append(
            SessyTimeEntity(hass, config_entry, "Stop Time",
                        system_settings_coordinator, "enabled_time",
                        update_stop_time,
                        entity_category=EntityCategory.CONFIG,
                        transform_function=stop_time_from_string)
            
        )

    async_add_entities(time_entities)
    
class SessyTimeEntity(SessyCoordinatorEntity, TimeEntity):
    def __init__(self, hass: HomeAssistant, config_entry: SessyConfigEntry, name: str,
                 coordinator: SessyCoordinator, data_key,
                 action_function: function,
                 entity_category: EntityCategory = None,
                 transform_function: function = None):
        
        super().__init__(hass=hass, config_entry=config_entry, name=name, 
                       coordinator=coordinator, data_key=data_key)
        self.pre_transform_function = transform_function
        self._attr_entity_category = entity_category
        self._attr_native_value = None
        self.action_function: function = action_function
    
    def update_from_cache(self):
        self._attr_available = self.cache_value != None
        if self.pre_transform_function: 
            self._attr_native_value = self.pre_transform_function(self.cache_value)
        else: 
            self._attr_native_value = self.cache_value
        
    async def async_set_value(self, value: time):
        try:
            await self.action_function(value)
        except SessyNotSupportedException as e:
            raise HomeAssistantError(f"Setting value for {self.name} failed: Not supported by device") from e
            
        except SessyConnectionException as e:
            raise HomeAssistantError(f"Setting value for {self.name} failed: Connection error") from e

        except Exception as e:
            raise HomeAssistantError(f"Setting value for {self.name} failed: {e.__class__}") from e
            
        await self.coordinator.async_refresh()
