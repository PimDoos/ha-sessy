from dataclasses import dataclass, field

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from sessypy.devices import SessyDevice

type SessyConfigEntry = ConfigEntry[SessyRuntimeData]

@dataclass
class SessyRuntimeData:
    device: SessyDevice = None
    device_info: DeviceInfo = None
    coordinators: dict[DataUpdateCoordinator] = field(default_factory=dict)