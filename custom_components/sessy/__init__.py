"""The Sessy integration."""
from __future__ import annotations
import logging


from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    Platform, CONF_USERNAME, CONF_PASSWORD, CONF_HOST
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from sessypy.devices import get_sessy_device
from sessypy.util import SessyLoginException, SessyConnectionException, SessyNotSupportedException

from .coordinator import refresh_coordinators, setup_coordinators, update_coordinator_options
from .models import SessyConfigEntry, SessyRuntimeData
from .util import generate_device_info

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.SENSOR, Platform.SELECT, Platform.NUMBER, Platform.SWITCH, Platform.TIME, Platform.UPDATE]

async def async_setup_entry(hass: HomeAssistant, config_entry: SessyConfigEntry) -> bool:
    """Set up Sessy from a config entry."""
   
    host = config_entry.data.get(CONF_HOST)

    _LOGGER.debug(f"Connecting to Sessy device at {host}")
    try:
        device = await get_sessy_device(
            host = host,
            username = config_entry.data.get(CONF_USERNAME),
            password = config_entry.data.get(CONF_PASSWORD),
        )

        # Prevent duplicate entries in older setups
        if not config_entry.unique_id:
            config_entry.unique_id = device.serial_number

    except SessyLoginException as e:
        raise ConfigEntryAuthFailed(f"Failed to connect to Sessy device at {host}: Authentication failed") from e
    except SessyNotSupportedException as e:
        raise ConfigEntryNotReady(f"Failed to connect to Sessy device at {host}: Device not supported") from e
    except SessyConnectionException as e:
        raise ConfigEntryNotReady(f"Failed to connect to Sessy device at {host}: Network error") from e
    
    if device is None:
        raise ConfigEntryNotReady(f"Failed to connect to Sessy device at {host}: Device type discovery failed")
    else:
        _LOGGER.info(f"Connection to {device.__class__} at {device.host} successful")

    config_entry.runtime_data = SessyRuntimeData(device = device)

    # Generate Device Info
    config_entry.runtime_data.device_info = await generate_device_info(hass, config_entry, device)
    config_entry.runtime_data.coordinators = await setup_coordinators(hass, config_entry, device)

    config_entry.add_update_listener(
        listener=update_coordinator_options
    )

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    # Refresh data once more to populate flattened data
    await refresh_coordinators(config_entry)

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: SessyConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)
    await config_entry.runtime_data.device.close()
    return unload_ok
