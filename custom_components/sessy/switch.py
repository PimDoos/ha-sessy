"""Switch to read data from Sessy"""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory

from sessypy.devices import SessyBattery, SessyDevice, SessyMeter
from sessypy.util import SessyNotSupportedException, SessyConnectionException

from .coordinator import SessyCoordinator, SessyCoordinatorEntity
from .models import SessyConfigEntry

import logging
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: SessyConfigEntry, async_add_entities):
    """Set up the Sessy switches"""

    device = config_entry.runtime_data.device
    coordinators = config_entry.runtime_data.coordinators
    switches = []

    if isinstance(device, SessyBattery):

        # Firmware or hardware-revision specific settings
        try:
            system_settings_coordinator: SessyCoordinator = coordinators[device.get_system_settings]
            settings: dict = system_settings_coordinator.raw_data
        
            # Eco mode controls (fw 1.6.8+)
            if settings.get("eco_nom_charge", None) != None:
                switches.append(
                    SessySettingSwitchEntity(hass, config_entry, "Eco NOM Charging Enabled",
                                system_settings_coordinator, "eco_nom_charge",
                                device.set_system_setting,
                                entity_category=EntityCategory.CONFIG)
                )
        except Exception as e:
            _LOGGER.warning(f"Error setting firmware specific settings: {e}")

    async_add_entities(switches)
    
class SessySettingSwitchEntity(SessyCoordinatorEntity, SwitchEntity):
    def __init__(self, hass: HomeAssistant, config_entry: SessyConfigEntry, name: str,
                 coordinator: SessyCoordinator, data_key,
                 action_function: function,
                 device_class: SwitchDeviceClass = None, 
                 entity_category: EntityCategory = None,
                 transform_function: function = None):
        
        super().__init__(hass=hass, config_entry=config_entry, name=name, 
                       coordinator=coordinator, data_key=data_key, 
                       transform_function=transform_function)


        self._attr_device_class = device_class
        self._attr_entity_category = entity_category
        
        self.action_function: function = action_function
    
    def update_from_cache(self):
        self._attr_available = self.cache_value != None
        self._attr_is_on = self.cache_value
        
    async def async_turn_on(self):
        await self._set_value(True)
            
    async def async_turn_off(self):
        await self._set_value(False)
    
    async def _set_value(self, value: bool):
        try:
            await self.action_function(self.data_key, value)
        except SessyNotSupportedException as e:
            raise HomeAssistantError(f"Setting value for {self.name} failed: Not supported by device") from e

        except SessyConnectionException as e:
            raise HomeAssistantError(f"Setting value for {self.name} failed: Connection error") from e

        except Exception as e:
            raise HomeAssistantError(f"Setting value for {self.name} failed: {e.__class__}") from e

        await self.coordinator.async_refresh()
