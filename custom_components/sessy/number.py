"""Number to read data from Sessy"""
from __future__ import annotations

from homeassistant.const import (
    UnitOfPower, UnitOfTime
)
from homeassistant.components.number import NumberEntity, NumberDeviceClass
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
    """Set up the Sessy numbers"""

    device: SessyDevice = config_entry.runtime_data.device
    coordinators: list[SessyCoordinator] = config_entry.runtime_data.coordinators
    
    numbers = []

    if isinstance(device, SessyBattery):
        power_status_coordinator = coordinators[device.get_power_status]
        numbers.append(
            SessyNumberEntity(hass, config_entry, "Power Setpoint",
                        power_status_coordinator, "sessy.power_setpoint",
                        device.set_power_setpoint,
                        NumberDeviceClass.POWER, UnitOfPower.WATT, -2200, 2200)
            
        )
        
        system_settings_coordinator = coordinators[device.get_system_settings]

        numbers.append(
            SessySettingNumberEntity(hass, config_entry, "Minimum Power",
                        system_settings_coordinator, "min_power",
                        NumberDeviceClass.POWER, UnitOfPower.WATT, 50, 2000,
                        entity_category=EntityCategory.CONFIG)
            
        )
        numbers.append(
            SessySettingNumberEntity(hass, config_entry, "Maximum Power",
                        system_settings_coordinator, "max_power",
                        NumberDeviceClass.POWER, UnitOfPower.WATT, 50, 2200,
                        entity_category=EntityCategory.CONFIG)
            
        )

        # Firmware or hardware-revision specific settings
        try:
            settings: dict = system_settings_coordinator.raw_data
            if "error" in settings:
                _LOGGER.warning(f"Sessy settings api returned an error:\n{ settings.get("error") }\nSome entities might not work until settings are saved in the Sessy portal or web UI.")

            # Noise controls
            if settings.get("disable_noise_level", True) == False:
                numbers.append(
                    SessySettingNumberEntity(hass, config_entry, "Noise Level",
                                system_settings_coordinator, "allowed_noise_level",
                                min_value=1, max_value=5,
                                entity_category=EntityCategory.CONFIG)
                    
                )
            
            # Eco mode controls (fw 1.6.8+)
            if settings.get("eco_charge_power", None) != None:
                numbers.append(
                    SessySettingNumberEntity(hass, config_entry, "Eco Charge Power",
                                system_settings_coordinator, "eco_charge_power",
                                NumberDeviceClass.POWER, UnitOfPower.WATT, 50, 2200,
                                entity_category=EntityCategory.CONFIG)
                    
                )
            if settings.get("eco_charge_hours", None) != None:
                numbers.append(
                    SessySettingNumberEntity(hass, config_entry, "Eco Charge Hours",
                                system_settings_coordinator, "eco_charge_hours",
                                NumberDeviceClass.DURATION, UnitOfTime.HOURS, 0, 24,
                                entity_category=EntityCategory.CONFIG)
                    
                )
        except Exception as e:
            _LOGGER.warning(f"Error setting up firmware specific settings: {e}\n{settings}")
        

    elif isinstance(device, SessyMeter):
        grid_target_coordinator = coordinators[device.get_grid_target]
        numbers.append(
            SessyNumberEntity(hass, config_entry, "Grid Target",
                        grid_target_coordinator, "grid_target",
                        device.set_grid_target,
                        NumberDeviceClass.POWER, UnitOfPower.WATT, -20000, 20000,
                        entity_category=EntityCategory.CONFIG)
            
        )

    async_add_entities(numbers)
    
class SessyNumberEntity(SessyCoordinatorEntity, NumberEntity):
    """Simple Number entity passing the value along to action_function"""
    def __init__(self, hass: HomeAssistant, config_entry: SessyConfigEntry, name: str,
                 coordinator: SessyCoordinator, data_key,
                 action_function: function,
                 device_class: NumberDeviceClass = None, unit_of_measurement = None,
                 min_value: float = None, max_value: float = None, 
                 entity_category: EntityCategory = None,
                 transform_function: function = None):
        
        super().__init__(hass=hass, config_entry=config_entry, name=name, 
                       coordinator=coordinator, data_key=data_key, 
                       transform_function=transform_function)


        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_entity_category = entity_category
        
        self.action_function: function = action_function
    
    def update_from_cache(self):
        self._attr_available = self.cache_value != None
        self._attr_native_value = self.cache_value
        
    async def async_set_native_value(self, value: float):
        try:
            await self.action_function(value)
        except SessyNotSupportedException as e:
            raise HomeAssistantError(f"Setting value for {self.name} failed: Not supported by device") from e

        except SessyConnectionException as e:
            raise HomeAssistantError(f"Setting value for {self.name} failed: Connection error") from e

        except Exception as e:
            raise HomeAssistantError(f"Setting value for {self.name} failed: {e.__class__}") from e

        await self.coordinator.async_refresh()

class SessySettingNumberEntity(SessyNumberEntity):
    """Number entity for updating Sessy system settings"""
    def __init__(self, hass: HomeAssistant, config_entry: SessyConfigEntry, name: str,
                 coordinator: SessyCoordinator, data_key,
                 device_class: NumberDeviceClass = None, unit_of_measurement = None,
                 min_value: float = None, max_value: float = None, 
                 entity_category: EntityCategory = None,
                 transform_function: function = None):
        
        device: SessyBattery = config_entry.runtime_data.device
        action_function = device.set_system_setting

        super().__init__(hass, config_entry, name,
                 coordinator, data_key,
                 action_function,
                 device_class, unit_of_measurement,
                 min_value, max_value, 
                 entity_category,
                 transform_function)
        
    async def async_set_native_value(self, value: float):
        try:
            await self.action_function(self.data_key, value)
        except SessyNotSupportedException as e:
            raise HomeAssistantError(f"Setting value for {self.name} failed: Not supported by device") from e

        except SessyConnectionException as e:
            raise HomeAssistantError(f"Setting value for {self.name} failed: Connection error") from e

        except Exception as e:
            raise HomeAssistantError(f"Setting value for {self.name} failed: {e.__class__}") from e

        await self.coordinator.async_refresh()
        