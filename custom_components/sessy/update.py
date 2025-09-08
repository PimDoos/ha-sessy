"""Update entities to control Sessy"""
from __future__ import annotations
from typing import Any, Callable, Optional



from homeassistant.core import HomeAssistant
from homeassistant.components.update import UpdateEntity, UpdateDeviceClass, UpdateEntityFeature
from homeassistant.const import ATTR_IDENTIFIERS
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr

from sessypy.const import SessyOtaTarget, SessyOtaState
from sessypy.devices import SessyDevice
from sessypy.util import SessyConnectionException, SessyNotSupportedException

from .const import DEFAULT_SCAN_INTERVAL, SCAN_INTERVAL_OTA_BUSY, SESSY_RELEASE_NOTES_URL
from .coordinator import SessyCoordinator, SessyCoordinatorEntity
from .models import SessyConfigEntry
from .util import unit_interval_to_percentage

import logging
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: SessyConfigEntry, async_add_entities):
    """Set up the Sessy updates"""

    device = config_entry.runtime_data.device
    updates = []

    # Treat Sessy Dongle and serial device (AC board) as one unit
    updates.append(
        SessyUpdate(hass, config_entry, "Firmware", SessyOtaTarget.SELF, action_target=SessyOtaTarget.ALL)
    )

    async_add_entities(updates)
    
class SessyUpdate(SessyCoordinatorEntity, UpdateEntity):
    def __init__(self, hass: HomeAssistant, config_entry: SessyConfigEntry, name: str,
                 cache_target: SessyOtaTarget, action_target: SessyOtaTarget = None,
                 transform_function: Optional[Callable] = None, enabled_default: bool = True):
        
        self.device = config_entry.runtime_data.device
        coordinator: SessyCoordinator = config_entry.runtime_data.coordinators[self.device.get_ota_status]
        self.coordinator = coordinator
        
        data_key = cache_target.name.lower()
        super().__init__(hass=hass, config_entry=config_entry, name=name, 
                       coordinator=coordinator, data_key=data_key, 
                       transform_function=transform_function)
        
        self._attr_entity_registry_enabled_default = enabled_default
        self._attr_device_class = UpdateDeviceClass.FIRMWARE
        self._attr_supported_features = UpdateEntityFeature.INSTALL | UpdateEntityFeature.PROGRESS
        self._attr_release_url = SESSY_RELEASE_NOTES_URL

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
            self.update_device_sw_version()

        # Skip version check if Sessy reports it is up to date or has not checked yet
        if state in [SessyOtaState.UP_TO_DATE.value, SessyOtaState.INACTIVE.value, SessyOtaState.CHECKING]:
            self._attr_latest_version = self._attr_installed_version
        else:
            self._attr_latest_version = self.cache_value.get("available_firmware", dict()).get("version", None)   
        
        if state == SessyOtaState.UPDATING.value:
            self.coordinator.update_interval = SCAN_INTERVAL_OTA_BUSY

            progress: int = self.cache_value.get("update_progress", None)
            if not progress:
                self._attr_in_progress = True
            else:
                self._attr_in_progress = unit_interval_to_percentage(progress)
        elif state == SessyOtaState.DONE.value:
            self._attr_in_progress = 100
        elif self.action_target == SessyOtaTarget.ALL:
            # When OtaTarget == ALL, serial device is updated first
            ota_data: dict = self.coordinator.get_data()

            cache_serial = ota_data.get(SessyOtaTarget.SERIAL.name.lower())
            if cache_serial is None:
                # Whoops, no data for serial available in cache. Skip until next update.
                pass
            elif cache_serial.get("state") == SessyOtaState.UPDATING.value:
                self.coordinator.update_interval = SCAN_INTERVAL_OTA_BUSY

                self._attr_in_progress = True
            else:
                self._attr_in_progress = False
        else:
            self._attr_in_progress = False

            # Restore scan interval
            self.coordinator.update_interval = DEFAULT_SCAN_INTERVAL

        
    def update_device_sw_version(self):
        try:
            device_registry = dr.async_get(self.hass)
            device = device_registry.async_get_device(self.device_info[ATTR_IDENTIFIERS])
            device_registry.async_update_device(device.id, sw_version=self.installed_version)
        except Exception as e:
            _LOGGER.warning(f"Could not write OTA status to device registry: {e}")

    async def async_install(self, version: str | None, backup: bool, **kwargs: Any) -> None:
        device: SessyDevice = self.config_entry.runtime_data.device
        try:
            await device.install_ota(self.action_target)
            self._attr_in_progress = True
        except SessyNotSupportedException as e:
            raise HomeAssistantError(f"Starting update for {self.name} failed: Not supported by device") from e
            
        except SessyConnectionException as e:
            raise HomeAssistantError(f"Starting update for {self.name} failed: Connection error") from e

        except Exception as e:
            raise HomeAssistantError(f"Starting update for {self.name} failed: {e.__class__}") from e
        
        _LOGGER.info("Setting OTA status update interval to lower interval (from install action)")

        self.coordinator.update_interval = SCAN_INTERVAL_OTA_BUSY
        await self.coordinator.async_request_refresh()

