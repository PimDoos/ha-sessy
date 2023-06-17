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

from .const import DOMAIN, SERIAL_NUMBER, SESSY_CACHE, SESSY_CACHE_TRACKERS, SESSY_CACHE_TRIGGERS, SESSY_DEVICE, SESSY_DEVICE_INFO
from .util import clear_cache_command, generate_device_info

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SELECT, Platform.NUMBER, Platform.TIME, Platform.UPDATE]


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Sessy from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = {}

    hass.data[DOMAIN][config_entry.entry_id][SERIAL_NUMBER] = config_entry.data.get(CONF_USERNAME).upper()
    
    # Prevent duplicate entries in older setups
    if not config_entry.unique_id:
        config_entry.unique_id = hass.data[DOMAIN][config_entry.entry_id][SERIAL_NUMBER]


    _LOGGER.debug(f"Connecting to Sessy device at {config_entry.data.get(CONF_HOST)}")
    try:
        device = await get_sessy_device(
            host = config_entry.data.get(CONF_HOST),
            username = config_entry.data.get(CONF_USERNAME),
            password = config_entry.data.get(CONF_PASSWORD),
        )
        
    except SessyLoginException:
        raise ConfigEntryAuthFailed
    except SessyNotSupportedException:
        raise ConfigEntryNotReady
    except SessyConnectionException:
        raise ConfigEntryNotReady
    
    if device is None:
        raise ConfigEntryNotReady
    else:
        _LOGGER.info(f"Connection to {device.__class__} at {device.host} successful")

    hass.data[DOMAIN][config_entry.entry_id][SESSY_DEVICE] = device

    # Generate Device Info
    hass.data[DOMAIN][config_entry.entry_id][SESSY_DEVICE_INFO] = await generate_device_info(hass, config_entry, device)


    hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE] = dict()
    hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE_TRACKERS] = dict()
    hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE_TRIGGERS] = dict()

    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, platform)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await clear_cache_command(hass, entry)
        await hass.data[DOMAIN][entry.entry_id][SESSY_DEVICE].close()
        if entry.entry_id in hass.data[DOMAIN]:
            hass.data[DOMAIN].pop(entry.entry_id)
            
    return unload_ok
