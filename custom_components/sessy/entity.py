"""Base entity for Sessy"""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from sessypy.devices import (
    SessyDevice,
)

from typing import Callable, Optional

from .const import (
    ENTITY_ERROR_THRESHOLD,
)
from .coordinator import SessyCoordinator, SessyEntityContext
from .models import SessyConfigEntry, SessyConnectedDeviceType

_LOGGER = logging.getLogger(__name__)

class SessyCoordinatorEntity(CoordinatorEntity):
    """Base Sessy Entity, coordinated by SessyCoordinator"""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: SessyConfigEntry,
        name: str,
        coordinator: SessyCoordinator,
        data_key: str,
        transform_function: Optional[Callable] = None,
        translation_key: str = None,
        availability_key: str = None,
        availability_test_value: str = None,
        connected_device_type: SessyConnectedDeviceType = SessyConnectedDeviceType.SELF,
    ):
        self.context = SessyEntityContext(data_key, transform_function, availability_key, availability_test_value)
        super().__init__(coordinator, self.context)
        self.hass = hass
        self.config_entry = config_entry

        self.transform_function = transform_function
        self.data_key = data_key
        self.cache_value = None
        self.availability_key = availability_key
        self.availability_test_value = availability_test_value

        device: SessyDevice = config_entry.runtime_data.device

        self._attr_name = name
        self._attr_has_entity_name = True
        self._attr_unique_id = f"sessy-{device.serial_number}-sensor-{name.replace(' ', '')}".lower()  # TODO Technical dept, this will cause issues if we ever need to change entity names
        self._attr_translation_key = translation_key
       
        self._attr_device_info = config_entry.runtime_data.device_info.get(
            connected_device_type,
            config_entry.runtime_data.device_info.get(SessyConnectedDeviceType.SELF)
        )

        self._update_failed_count = 0

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            self.copy_from_cache()
            self._update_failed_count = 0
        except Exception as e:
            self._update_failed_count += 1
            message = f"Updating entity '{self.name}' failed for {self._update_failed_count} consecutive attempts. Exception occurred: '{e}'"
            self.cache_value = None
            if self._update_failed_count == ENTITY_ERROR_THRESHOLD:
                # Log as warning once attempts exceed threshold
                _LOGGER.warning(message)
            else:
                _LOGGER.debug(message)

        finally:
            self.update_from_cache()
            self.async_write_ha_state()

    def copy_from_cache(self):
        value, available = self.coordinator.data.get(self.context, tuple((None, False)))
        self.cache_value = value
        self._attr_available = available

        if self.cache_value is None:
            raise TypeError(
                f"Key {self.data_key} has no value in coordinator {self.coordinator.name}"
            )

    def update_from_cache(self):
        """Entity function to write the latest cache value to the proper attributes. Implemented on platform level."""
        raise NotImplementedError()
    
    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return super().available and self._attr_available