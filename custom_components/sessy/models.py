from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from sessypy.devices import SessyDevice

if TYPE_CHECKING:
    from .coordinator import SessyCoordinator

type SessyConfigEntry = ConfigEntry[SessyRuntimeData]

@dataclass
class SessyRuntimeData:
    device: SessyDevice = None
    device_info: DeviceInfo = None
    coordinators: dict[SessyCoordinator] = dict()