"""Update entities to control Sessy"""
from __future__ import annotations
from enum import Enum
from typing import Any

import logging
_LOGGER = logging.getLogger(__name__)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.update import UpdateEntity, UpdateDeviceClass, UpdateEntityFeature
from homeassistant.const import ATTR_SW_VERSION

from sessypy.const import SessyApiCommand, SessyOtaTarget, SessyOtaState
from sessypy.devices import SessyBattery, SessyDevice, SessyP1Meter

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, SESSY_DEVICE, SCAN_INTERVAL_OTA, SCAN_INTERVAL_OTA_CHECK, SESSY_DEVICE_INFO
from .util import add_cache_command, trigger_cache_update, unit_interval_to_percentage
from .sessyentity import SessyEntity

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    """Set up the Sessy updates"""

    device = hass.data[DOMAIN][config_entry.entry_id][SESSY_DEVICE]
    updates = []

    await add_cache_command(hass, config_entry, SessyApiCommand.OTA_CHECK, SCAN_INTERVAL_OTA_CHECK)
    await add_cache_command(hass, config_entry, SessyApiCommand.OTA_STATUS, SCAN_INTERVAL_OTA)
    
    if isinstance(device, SessyBattery):
        updates.append(
            SessyUpdate(hass, config_entry, "Battery Dongle", SessyOtaTarget.SELF)
        )

        updates.append(
            SessyUpdate(hass, config_entry, "Battery", SessyOtaTarget.SERIAL)
		)
    elif isinstance(device, SessyP1Meter):
        updates.append(
            SessyUpdate(hass, config_entry, "Dongle", SessyOtaTarget.SELF)
        )

    async_add_entities(updates)
    
class SessyUpdate(SessyEntity, UpdateEntity):
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, name: str,
                 update_target: SessyOtaTarget, transform_function: function = None
                 ):
        
        cache_command = SessyApiCommand.OTA_STATUS
        cache_key = update_target.name.lower()
        super().__init__(hass=hass, config_entry=config_entry, name=name, 
                       cache_command=cache_command, cache_key=cache_key, 
                       transform_function=transform_function)
        
        self._attr_device_class = UpdateDeviceClass.FIRMWARE
        self._attr_supported_features = UpdateEntityFeature.INSTALL + UpdateEntityFeature.PROGRESS

        self.update_target = update_target
        self.cache_value = dict()
       
    def update_from_cache(self):
        if not self.cache_value:
            self.cache_value = dict()
            self._attr_available = False
        else:
            self._attr_available = True

        state = self.cache_value.get("state", SessyOtaState.INACTIVE.value)

        
        self._attr_installed_version = self.cache_value.get("installed_firmware", dict()).get("version", None)

        if self.update_target == SessyOtaTarget.SELF:
            try: 
                self.hass.data[DOMAIN][self.config_entry.entry_id][SESSY_DEVICE_INFO][ATTR_SW_VERSION] = self._attr_installed_version
            except:
                _LOGGER.warning("Could not write OTA status to device info")

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
        
        await device.install_ota(self.update_target)
        await trigger_cache_update(self.hass, self.config_entry, self.cache_command)
