from dataclasses import dataclass, field
from enum import StrEnum

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from sessypy.devices import SessyDevice

type SessyConfigEntry = ConfigEntry[SessyRuntimeData]


@dataclass
class SessyRuntimeData:
    device: SessyDevice = None
    device_info: DeviceInfo = None
    connected_device_info: dict[DeviceInfo] = field(default_factory=dict)
    coordinators: dict[DataUpdateCoordinator] = field(default_factory=dict)

class SessyConnectedDeviceType(StrEnum):
    SELF = "self"
    BATTERY = "battery"
    P1_METER = "p1_meter"
    P1_GAS_METER = "p1_gas_meter"
    MODBUS_METER = "modbus_meter"

    