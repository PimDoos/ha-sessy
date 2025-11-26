"""BinarySensor to read data from Sessy"""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from sessypy.devices import SessyBattery, SessyDevice

from typing import Callable, Optional

from .coordinator import SessyCoordinator, SessyCoordinatorEntity
from .models import SessyConfigEntry

import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: SessyConfigEntry, async_add_entities
):
    """Set up the Sessy binary_sensors"""

    device: SessyDevice = config_entry.runtime_data.device
    coordinators = config_entry.runtime_data.coordinators
    binary_sensors = []

    if isinstance(device, SessyBattery):
        # Power Status
        try:
            power_status_coordinator: SessyCoordinator = coordinators[
                device.get_power_status
            ]
            power_status: dict = power_status_coordinator.raw_data

            if "strategy_overridden" in power_status.get("sessy", dict()):
                binary_sensors.append(
                    SessyBinarySensor(
                        hass,
                        config_entry,
                        "Strategy Override",
                        power_status_coordinator,
                        "sessy.strategy_overridden",
                        BinarySensorDeviceClass.RUNNING,
                        entity_category=EntityCategory.DIAGNOSTIC,
                    )
                )

        except Exception as e:
            _LOGGER.warning(f"Error setting up power status binary_sensors: {e}")

    async_add_entities(binary_sensors)


class SessyBinarySensor(SessyCoordinatorEntity, BinarySensorEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: SessyConfigEntry,
        name: str,
        coordinator: SessyCoordinatorEntity,
        data_key,
        device_class: BinarySensorDeviceClass = None,
        transform_function: Optional[Callable] = None,
        entity_category: EntityCategory = None,
        enabled_default: bool = True,
    ):
        super().__init__(
            hass=hass,
            config_entry=config_entry,
            name=name,
            coordinator=coordinator,
            data_key=data_key,
            transform_function=transform_function,
        )

        self._attr_device_class = device_class
        self._attr_entity_category = entity_category

        self._attr_entity_registry_enabled_default = enabled_default

    def update_from_cache(self):
        self._attr_is_on = self.cache_value
