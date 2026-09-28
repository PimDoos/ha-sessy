"""Switch to read data from Sessy"""

from __future__ import annotations

import logging
from collections.abc import Callable

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from sessypy.devices import SessyBattery
from sessypy.util import SessyConnectionException, SessyNotSupportedException

from .coordinator import SessyCoordinator
from .entity import SessyCoordinatorEntity
from .models import SessyConfigEntry, SessyConnectedDeviceType

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: SessyConfigEntry, async_add_entities
):
    """Set up the Sessy switches"""

    device = config_entry.runtime_data.device
    coordinators = config_entry.runtime_data.coordinators
    switches = []

    if isinstance(device, SessyBattery):
        # Firmware or hardware-revision specific settings
        try:
            system_settings_coordinator: SessyCoordinator = coordinators[
                device.get_system_settings
            ]
            settings: dict = system_settings_coordinator.raw_data

            # Eco mode controls (fw 1.6.8+)
            if settings.get("eco_nom_charge", None) is not None:
                switches.append(
                    SessySettingSwitchEntity(
                        hass,
                        config_entry,
                        "Eco NOM Charging Enabled",
                        system_settings_coordinator,
                        "eco_nom_charge",
                        device.set_system_setting,
                        entity_category=EntityCategory.CONFIG,
                        connected_device_type=SessyConnectedDeviceType.BATTERY,
                    )
                )

            # Temperature limit controls (fw 1.9.0+)
            if settings.get("pack_temp_limit_enabled", None) is not None:
                switches.append(
                    SessySettingSwitchEntity(
                        hass,
                        config_entry,
                        "Temperature Limit Enabled",
                        system_settings_coordinator,
                        "pack_temp_limit_enabled",
                        device.set_system_setting,
                        entity_category=EntityCategory.CONFIG,
                        connected_device_type=SessyConnectedDeviceType.BATTERY,
                    )
                )

        except Exception as e:
            _LOGGER.warning("Error setting firmware specific settings: %s", e)

    async_add_entities(switches)


class SessySettingSwitchEntity(SessyCoordinatorEntity, SwitchEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: SessyConfigEntry,
        name: str,
        coordinator: SessyCoordinator,
        data_key: str,
        action_function: Callable,
        device_class: SwitchDeviceClass = None,
        entity_category: EntityCategory = None,
        transform_function: Callable | None = None,
        connected_device_type: SessyConnectedDeviceType = SessyConnectedDeviceType.SELF,
    ):
        super().__init__(
            hass=hass,
            config_entry=config_entry,
            name=name,
            coordinator=coordinator,
            data_key=data_key,
            transform_function=transform_function,
            connected_device_type=connected_device_type,
        )

        self._attr_device_class = device_class
        self._attr_entity_category = entity_category

        self.action_function: Callable = action_function

    def update_from_cache(self):
        self._attr_is_on = self.cache_value

    async def async_turn_on(self, **kwargs):
        await self._set_value(True)

    async def async_turn_off(self, **kwargs):
        await self._set_value(False)

    async def _set_value(self, value: bool):
        try:
            await self.action_function(self.data_key, value)
        except SessyNotSupportedException as e:
            raise HomeAssistantError(
                f"Setting value for {self.name} failed: Not supported by device"
            ) from e

        except SessyConnectionException as e:
            raise HomeAssistantError(
                f"Setting value for {self.name} failed: Connection error"
            ) from e

        except Exception as e:
            raise HomeAssistantError(
                f"Setting value for {self.name} failed: {e.__class__}"
            ) from e

        await self.coordinator.async_refresh()
