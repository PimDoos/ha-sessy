"""Sessy integration data models"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from sessypy.devices import SessyDevice

type SessyConfigEntry = ConfigEntry[SessyRuntimeData]


class SessyConnectedDeviceType(StrEnum):
    """Types devices connected to the Sessy device"""

    SELF = "self"
    BATTERY = "battery"
    P1_METER = "p1_meter"
    P1_GAS_METER = "p1_gas_meter"
    MODBUS_METER = "modbus_meter"


@dataclass
class SessyRuntimeData:
    """Runtime data for the Sessy integration"""

    device: SessyDevice
    device_info: dict[SessyConnectedDeviceType, DeviceInfo]
    coordinators: dict[Callable, DataUpdateCoordinator]
