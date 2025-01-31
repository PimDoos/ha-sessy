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

from .const import DOMAIN, SERIAL_NUMBER, SESSY_DEVICE, SESSY_DEVICE_INFO
from .util import clear_cache_command, generate_device_info, setup_cache, setup_cache_commands

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.SENSOR, Platform.SELECT, Platform.NUMBER, Platform.SWITCH, Platform.TIME, Platform.UPDATE]


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Sessy from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = {}

    hass.data[DOMAIN][config_entry.entry_id][SERIAL_NUMBER] = config_entry.data.get(CONF_USERNAME).upper()
    
    # Prevent duplicate entries in older setups
    if not config_entry.unique_id:
        config_entry.unique_id = hass.data[DOMAIN][config_entry.entry_id][SERIAL_NUMBER]

    host = config_entry.data.get(CONF_HOST)

    _LOGGER.debug(f"Connecting to Sessy device at {host}")
    try:
        device = await get_sessy_device(
            host = host,
            username = config_entry.data.get(CONF_USERNAME),
            password = config_entry.data.get(CONF_PASSWORD),
        )
        
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

    hass.data[DOMAIN][config_entry.entry_id][SESSY_DEVICE] = device

    # Setup caching
    await setup_cache(hass, config_entry)
    await setup_cache_commands(hass, config_entry, device)

    # Update cache command on options flow update
    async def update_cache_commands(hass, config_entry):
        await setup_cache_commands(hass, config_entry, device, setup=False)

    config_entry.add_update_listener(
        listener=update_cache_commands
    )

    # Generate Device Info
    hass.data[DOMAIN][config_entry.entry_id][SESSY_DEVICE_INFO] = await generate_device_info(hass, config_entry, device)

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await clear_cache_command(hass, entry)
        await hass.data[DOMAIN][entry.entry_id][SESSY_DEVICE].close()
        if entry.entry_id in hass.data[DOMAIN]:
            hass.data[DOMAIN].pop(entry.entry_id)
            
    return unload_ok
