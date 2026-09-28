"""BinarySensor to read data from Sessy"""

from __future__ import annotations

import logging
from collections.abc import Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from sessypy.devices import SessyBattery, SessyDevice

from .coordinator import SessyCoordinator
from .entity import SessyCoordinatorEntity
from .models import SessyConfigEntry, SessyConnectedDeviceType

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
        power_status_coordinator: SessyCoordinator = coordinators[
            device.get_power_status
        ]
        power_status: dict = power_status_coordinator.raw_data

        if "strategy_overridden" in power_status.get("sessy", {}):
            binary_sensors.append(
                SessyBinarySensor(
                    hass,
                    config_entry,
                    "Strategy Override",
                    power_status_coordinator,
                    "sessy.strategy_overridden",
                    BinarySensorDeviceClass.RUNNING,
                    entity_category=EntityCategory.DIAGNOSTIC,
                    connected_device_type=SessyConnectedDeviceType.BATTERY,
                )
            )

    async_add_entities(binary_sensors)


class SessyBinarySensor(SessyCoordinatorEntity, BinarySensorEntity):
    """Sessy binary sensor entities"""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: SessyConfigEntry,
        name: str,
        coordinator: SessyCoordinatorEntity,
        data_key,
        device_class: BinarySensorDeviceClass = None,
        transform_function: Callable | None = None,
        entity_category: EntityCategory = None,
        enabled_default: bool = True,
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

        self._attr_entity_registry_enabled_default = enabled_default

    def update_from_cache(self):
        self._attr_is_on = self.cache_value
