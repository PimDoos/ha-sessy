"""Update entities to control Sessy"""

from __future__ import annotations
from typing import Any, Callable, Optional


from homeassistant.core import HomeAssistant
from homeassistant.components.update import (
    UpdateEntity,
    UpdateDeviceClass,
    UpdateEntityFeature,
)
from homeassistant.exceptions import HomeAssistantError

from sessypy.const import SessyOtaTarget, SessyOtaState
from sessypy.devices import SessyDevice
from sessypy.util import SessyConnectionException, SessyNotSupportedException

from custom_components.sessy.device import update_sw_version

from .const import (
    DEFAULT_SCAN_INTERVAL,
    SCAN_INTERVAL_OTA_BUSY,
    SESSY_RELEASE_NOTES_URL,
)
from .coordinator import SessyCoordinator
from .entity import SessyCoordinatorEntity
from .models import SessyConfigEntry, SessyConnectedDeviceType
from .util import unit_interval_to_percentage

import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: SessyConfigEntry, async_add_entities
):
    """Set up the Sessy update_entities"""

    update_entities = []

    # Treat Sessy Dongle and serial device (AC board) as one unit
    update_entities.append(SessyUpdate(hass, config_entry, "Firmware"))

    async_add_entities(update_entities)


class SessyUpdate(SessyCoordinatorEntity, UpdateEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: SessyConfigEntry,
        name: str,
        transform_function: Optional[Callable] = None,
        enabled_default: bool = True,
        connected_device_type: SessyConnectedDeviceType = SessyConnectedDeviceType.SELF,
    ):
        self.device = config_entry.runtime_data.device
        coordinator: SessyCoordinator = config_entry.runtime_data.coordinators[
            self.device.get_ota_status
        ]
        self.coordinator = coordinator

        super().__init__(
            hass=hass,
            config_entry=config_entry,
            name=name,
            coordinator=coordinator,
            data_key=None,
            transform_function=transform_function,
            connected_device_type=connected_device_type,
        )

        self._attr_entity_registry_enabled_default = enabled_default
        self._attr_device_class = UpdateDeviceClass.FIRMWARE
        self._attr_supported_features = (
            UpdateEntityFeature.INSTALL | UpdateEntityFeature.PROGRESS
        )
        self._attr_release_url = SESSY_RELEASE_NOTES_URL

        self.cache_value = dict()
        self.serial_installed_version = None

    def update_from_cache(self):
        if not self.cache_value:
            self.cache_value = dict()
            self._attr_available = False
        else:
            self._attr_available = True

        ota_self = self.cache_value.get("self")
        ota_serial = self.cache_value.get("serial")

        ota_states = [
            ota_self.get("state", SessyOtaState.DISABLED),
            ota_serial.get("state", SessyOtaState.DISABLED),
        ]

        ota_progress = [
            ota_self.get("update_progress", 0),
            ota_serial.get("update_progress", 0),
        ]

        if "available_firmware" in ota_self:
            if ota_self["available_firmware"].get("version", "") != "":
                self._attr_latest_version = ota_self["available_firmware"]["version"]

        if "installed_firmware" in ota_self:
            if ota_self["installed_firmware"].get("version", "") != "":
                last_installed_version = self._attr_installed_version
                self._attr_installed_version = ota_self["installed_firmware"]["version"]

                # Check if firmware version has changed and update device registry
                if last_installed_version != self._attr_installed_version:
                    update_sw_version(
                        self.hass, self.config_entry, self._attr_installed_version
                    )

        if "installed_firmware" in ota_serial:
            if ota_serial["installed_firmware"].get("version", "") != "":
                last_installed_version_serial = self.serial_installed_version
                self.serial_installed_version = ota_serial["installed_firmware"][
                    "version"
                ]

                # Check if firmware version has changed and update device registry
                if last_installed_version_serial != self.serial_installed_version:
                    update_sw_version(
                        self.hass,
                        self.config_entry,
                        self.serial_installed_version,
                        SessyConnectedDeviceType.BATTERY,
                    )

        # Determine overall state based on both serial and self OTA status
        if SessyOtaState.UPDATING in ota_states:
            self._attr_in_progress = True
            if ota_states[1] == SessyOtaState.DISABLED:
                self._attr_update_percentage = unit_interval_to_percentage(
                    ota_progress[0]
                )
            else:
                self._attr_update_percentage = (
                    unit_interval_to_percentage(ota_progress[0]) / 2
                    + unit_interval_to_percentage(ota_progress[1]) / 2
                )
        elif ota_states[0] == SessyOtaState.DONE and ota_states[1] in [
            SessyOtaState.DONE,
            SessyOtaState.DISABLED,
        ]:
            self._attr_in_progress = True
            self._attr_update_percentage = 100
        else:
            self._attr_in_progress = False

        # Poll more frequently if an update is in progress
        if self._attr_in_progress:
            self.coordinator.update_interval = SCAN_INTERVAL_OTA_BUSY
        else:
            # Restore scan interval
            self.coordinator.update_interval = DEFAULT_SCAN_INTERVAL

    async def async_install(
        self, version: str | None, backup: bool, **kwargs: Any
    ) -> None:
        device: SessyDevice = self.config_entry.runtime_data.device
        try:
            await device.install_ota(SessyOtaTarget.ALL)
            self._attr_in_progress = True
        except SessyNotSupportedException as e:
            raise HomeAssistantError(
                f"Starting update for {self.name} failed: Not supported by device"
            ) from e

        except SessyConnectionException as e:
            raise HomeAssistantError(
                f"Starting update for {self.name} failed: Connection error"
            ) from e

        except Exception as e:
            raise HomeAssistantError(
                f"Starting update for {self.name} failed: {e.__class__}"
            ) from e

        _LOGGER.info(
            "Setting OTA status update interval to lower interval (from install action)"
        )

        self.coordinator.update_interval = SCAN_INTERVAL_OTA_BUSY
        await self.coordinator.async_request_refresh()
