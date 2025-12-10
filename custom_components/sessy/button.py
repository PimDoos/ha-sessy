"""Button entities to control Sessy"""

from __future__ import annotations


from homeassistant.core import HomeAssistant
from homeassistant.components.button import ButtonEntity, ButtonDeviceClass
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory

from sessypy.devices import SessyDevice
from sessypy.util import SessyConnectionException, SessyNotSupportedException

from typing import Callable, Optional

from .coordinator import SessyCoordinator, SessyCoordinatorEntity
from .models import SessyConfigEntry


async def async_setup_entry(
    hass: HomeAssistant, config_entry: SessyConfigEntry, async_add_entities
):
    """Set up the Sessy buttons"""

    device: SessyDevice = config_entry.runtime_data.device
    coordinators = config_entry.runtime_data.coordinators

    buttons = []

    buttons.append(
        SessyButton(
            hass,
            config_entry,
            "Dongle Restart",
            coordinators[device.get_system_info],
            "status",
            device.restart,
            device_class=ButtonDeviceClass.RESTART,
            entity_category=EntityCategory.DIAGNOSTIC,
        )
    )
    buttons.append(
        SessyButton(
            hass,
            config_entry,
            "Check for updates",
            coordinators[device.get_ota_status],
            "status",
            device.check_ota,
            entity_category=EntityCategory.DIAGNOSTIC,
        )
    )

    async_add_entities(buttons)


class SessyButton(SessyCoordinatorEntity, ButtonEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: SessyConfigEntry,
        name: str,
        coordinator: SessyCoordinator,
        data_key: str,
        action_function: Callable,
        device_class: ButtonDeviceClass = None,
        entity_category: EntityCategory = None,
        transform_function: Optional[Callable] = None,
        translation_key: str = None,
    ):
        super().__init__(
            hass=hass,
            config_entry=config_entry,
            name=name,
            coordinator=coordinator,
            data_key=data_key,
            transform_function=transform_function,
            translation_key=translation_key,
        )

        self.action_function = action_function
        self._attr_device_class = device_class
        self._attr_entity_category = entity_category

    def update_from_cache(self):
        # No update necessary, availability is set from coordinator
        pass

    async def async_press(self):
        try:
            await self.action_function()
        except SessyNotSupportedException as e:
            raise HomeAssistantError(
                f"Sending command for {self.name} failed: Not supported by device"
            ) from e

        except SessyConnectionException as e:
            raise HomeAssistantError(
                f"Sending command for {self.name} failed: Connection error"
            ) from e

        except Exception as e:
            raise HomeAssistantError(
                f"Sending command for {self.name} failed: {e.__class__}"
            ) from e
