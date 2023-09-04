"""Update entities to control Sessy"""
from __future__ import annotations
from enum import Enum
from typing import Any

import logging

from sessypy.util import SessyConnectionException, SessyNotSupportedException
_LOGGER = logging.getLogger(__name__)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.update import UpdateEntity, UpdateDeviceClass, UpdateEntityFeature
from homeassistant.const import ATTR_IDENTIFIERS
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr

from sessypy.const import SessyApiCommand, SessyOtaTarget, SessyOtaState
from sessypy.devices import SessyBattery, SessyDevice, SessyP1Meter, SessyCTMeter

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, SESSY_DEVICE, SCAN_INTERVAL_OTA, SCAN_INTERVAL_OTA_CHECK, SESSY_DEVICE_INFO
from .util import add_cache_command, trigger_cache_update, unit_interval_to_percentage
from .sessyentity import SessyEntity

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    """Set up the Sessy updates"""

    device = hass.data[DOMAIN][config_entry.entry_id][SESSY_DEVICE]
    updates = []


    # TODO Disabled by default for now, remove later
    if isinstance(device, SessyBattery):
        updates.append(
            SessyUpdate(hass, config_entry, "Battery Dongle", SessyOtaTarget.SELF, enabled_default=False)
        )
        updates.append(
            SessyUpdate(hass, config_entry, "Battery", SessyOtaTarget.SERIAL, enabled_default=False)
		)
    
    elif isinstance(device, SessyP1Meter) or isinstance(device, SessyCTMeter):
        updates.append(
            SessyUpdate(hass, config_entry, "Dongle", SessyOtaTarget.SELF, enabled_default=False)
        )

    # Treat Sessy Dongle and serial device (AC board) as one unit
    updates.append(
        SessyUpdate(hass, config_entry, "Firmware", SessyOtaTarget.SELF, action_target=SessyOtaTarget.ALL)
    )

    async_add_entities(updates)
    
class SessyUpdate(SessyEntity, UpdateEntity):
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, name: str,
                 cache_target: SessyOtaTarget, action_target: SessyOtaTarget = None,
                 transform_function: function = None, enabled_default: bool = True):
        
        cache_command = SessyApiCommand.OTA_STATUS
        cache_key = cache_target.name.lower()
        super().__init__(hass=hass, config_entry=config_entry, name=name, 
                       cache_command=cache_command, cache_key=cache_key, 
                       transform_function=transform_function)
        
        self._attr_entity_registry_enabled_default = enabled_default
        self._attr_device_class = UpdateDeviceClass.FIRMWARE
        self._attr_supported_features = UpdateEntityFeature.INSTALL + UpdateEntityFeature.PROGRESS

        self.cache_target = cache_target
        if action_target:
            self.action_target = action_target
        else:
            self.action_target = cache_target

        self.cache_value = dict()
       
    def update_from_cache(self):
        if not self.cache_value:
            self.cache_value = dict()
            self._attr_available = False
        else:
            self._attr_available = True

        state = self.cache_value.get("state", SessyOtaState.INACTIVE.value)

        last_installed_version = self._attr_installed_version
        self._attr_installed_version = self.cache_value.get("installed_firmware", dict()).get("version", None)

        # Write new firmware version to device registry
        if self.cache_target == SessyOtaTarget.SELF and last_installed_version != self._attr_installed_version:
            try:
                device_registry = dr.async_get(self.hass)
                device = device_registry.async_get_device(self.device_info[ATTR_IDENTIFIERS])
                device_registry.async_update_device(device.id, sw_version=self.installed_version)
            except:
                _LOGGER.warning("Could not write OTA status to device registry")

        # Skip version check if Sessy reports it is up to date or has not checked yet
        if state in [SessyOtaState.UP_TO_DATE.value, SessyOtaState.INACTIVE.value]:
            self._attr_latest_version = self._attr_installed_version
        else:
            self._attr_latest_version = self.cache_value.get("available_firmware", dict()).get("version", None)   
        
        if state == SessyOtaState.UPDATING.value:
            progress: int = self.cache_value.get("update_progress", None)
            if not progress:
                self._attr_in_progress = True
            else:
                self._attr_in_progress = unit_interval_to_percentage(progress)
        elif state == SessyOtaState.DONE.value:
            self._attr_in_progress = 100
        else:
            self._attr_in_progress = False
        

    async def async_install(self, version: str | None, backup: bool, **kwargs: Any) -> None:
        device: SessyDevice = self.hass.data[DOMAIN][self.config_entry.entry_id][SESSY_DEVICE]
        try:
            await device.install_ota(self.action_target)
        except SessyNotSupportedException as e:
            raise HomeAssistantError(f"Starting update for {self.name} failed: Not supported by device") from e
            
        except SessyConnectionException as e:
            raise HomeAssistantError(f"Starting update for {self.name} failed: Connection error") from e

        except Exception as e:
            raise HomeAssistantError(f"Starting update for {self.name} failed: {e.__class__}") from e
        
        await trigger_cache_update(self.hass, self.config_entry, self.cache_command)
