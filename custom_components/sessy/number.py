"""Number to read data from Sessy"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfPower, UnitOfTime
)
from homeassistant.components.number import NumberEntity, NumberDeviceClass
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
    """Set up the Sessy numbers"""

    device = hass.data[DOMAIN][config_entry.entry_id][SESSY_DEVICE]
    numbers = []

    if isinstance(device, SessyBattery):
        numbers.append(
            SessyNumber(hass, config_entry, "Power Setpoint",
                        SessyApiCommand.POWER_STATUS, "sessy.power_setpoint",
                        SessyApiCommand.POWER_SETPOINT, "setpoint",
                        NumberDeviceClass.POWER, UnitOfPower.WATT, -2200, 2200)
            
        )

        async def partial_update_settings(key,value):
            settings: dict = await device.get_system_settings()
            settings[key] = value
            return settings
        
        numbers.append(
            SessyNumber(hass, config_entry, "Minimum Power",
                        SessyApiCommand.SYSTEM_SETTINGS, "min_power",
                        SessyApiCommand.SYSTEM_SETTINGS, "min_power",
                        NumberDeviceClass.POWER, UnitOfPower.WATT, 50, 2000,
                        entity_category=EntityCategory.CONFIG,
                        action_function=partial_update_settings)
            
        )
        numbers.append(
            SessyNumber(hass, config_entry, "Maximum Power",
                        SessyApiCommand.SYSTEM_SETTINGS, "max_power",
                        SessyApiCommand.SYSTEM_SETTINGS, "max_power",
                        NumberDeviceClass.POWER, UnitOfPower.WATT, 50, 2200,
                        entity_category=EntityCategory.CONFIG,
                        action_function=partial_update_settings)
            
        )

        # Firmware or hardware-revision specific settings
        try:
            settings: dict = get_cache_command(hass, config_entry, SessyApiCommand.SYSTEM_SETTINGS)
            if "error" in settings:
                _LOGGER.warning(f"Sessy settings api returned an error:\n{ settings.get("error") }\nSome entities might not work until settings are saved in the Sessy portal or web UI.")

            # Noise controls
            if settings.get("disable_noise_level", True) == False:
                numbers.append(
                    SessyNumber(hass, config_entry, "Noise Level",
                                SessyApiCommand.SYSTEM_SETTINGS, "allowed_noise_level",
                                SessyApiCommand.SYSTEM_SETTINGS, "allowed_noise_level",
                                min_value=1, max_value=5,
                                entity_category=EntityCategory.CONFIG,
                                action_function=partial_update_settings)
                    
                )
            
            # Eco mode controls (fw 1.6.8+)
            if settings.get("eco_charge_power", None) != None:
                numbers.append(
                    SessyNumber(hass, config_entry, "Eco Charge Power",
                                SessyApiCommand.SYSTEM_SETTINGS, "eco_charge_power",
                                SessyApiCommand.SYSTEM_SETTINGS, "eco_charge_power",
                                NumberDeviceClass.POWER, UnitOfPower.WATT, 50, 2200,
                                entity_category=EntityCategory.CONFIG,
                                action_function=partial_update_settings)
                    
                )
            if settings.get("eco_charge_hours", None) != None:
                numbers.append(
                    SessyNumber(hass, config_entry, "Eco Charge Hours",
                                SessyApiCommand.SYSTEM_SETTINGS, "eco_charge_hours",
                                SessyApiCommand.SYSTEM_SETTINGS, "eco_charge_hours",
                                NumberDeviceClass.DURATION, UnitOfTime.HOURS, 0, 24,
                                entity_category=EntityCategory.CONFIG,
                                action_function=partial_update_settings)
                    
                )
        except Exception as e:
            _LOGGER.warning(f"Error setting up firmware specific settings: {e}\n{settings}")
        

    elif isinstance(device, SessyMeter):
         numbers.append(
            SessyNumber(hass, config_entry, "Grid Target",
                        SessyApiCommand.METER_GRID_TARGET, "grid_target",
                        SessyApiCommand.METER_GRID_TARGET, "grid_target",
                        NumberDeviceClass.POWER, UnitOfPower.WATT, -20000, 20000,
                        entity_category=EntityCategory.CONFIG)
            
        )

    async_add_entities(numbers)
    
class SessyNumber(SessyEntity, NumberEntity):
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, name: str,
                 cache_command: SessyApiCommand, cache_key,
                 action_command: SessyApiCommand, action_key: SessyApiCommand,
                 device_class: NumberDeviceClass = None, unit_of_measurement = None,
                 min_value: float = None, max_value: float = None, 
                 entity_category: EntityCategory = None,
                 transform_function: function = None, action_function: function = None):
        
        super().__init__(hass=hass, config_entry=config_entry, name=name, 
                       cache_command=cache_command, cache_key=cache_key, 
                       transform_function=transform_function)


        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_entity_category = entity_category
        
        self.action_command = action_command
        self.action_key = action_key
        self.action_function: function = action_function
    
    def update_from_cache(self):
        self._attr_available = self.cache_value != None
        self._attr_native_value = self.cache_value
        
    async def async_set_native_value(self, value: float):
        device: SessyDevice = self.hass.data[DOMAIN][self.config_entry.entry_id][SESSY_DEVICE]
        try:
            if not self.action_function:
                payload = {self.action_key: int(value)}
            else:
                payload = await self.action_function(self.action_key, int(value))
                
            await device.api.post(self.action_command, payload)
        except SessyNotSupportedException as e:
            raise HomeAssistantError(f"Setting value for {self.name} failed: Not supported by device") from e

        except SessyConnectionException as e:
            raise HomeAssistantError(f"Setting value for {self.name} failed: Connection error") from e

        except Exception as e:
            raise HomeAssistantError(f"Setting value for {self.name} failed: {e.__class__}") from e

        await trigger_cache_update(self.hass, self.config_entry, self.cache_command)
