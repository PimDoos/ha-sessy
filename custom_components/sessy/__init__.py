"""The Sessy integration."""
from __future__ import annotations
from datetime import timedelta
import datetime
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, CONF_USERNAME, CONF_PASSWORD, CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from homeassistant.helpers.event import async_track_time_interval

from homeassistant.util import dt as dt_util

from sessypy.devices import get_sessy_device
from sessypy.util import SessyLoginException, SessyConnectionException, SessyNotSupportedException

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, SESSY_CACHE, SESSY_CACHE_POWER_STATUS, SESSY_DEVICE, SESSY_POLL_LISTENER

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Sessy from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = {}

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

    hass.data[DOMAIN][config_entry.entry_id][SESSY_DEVICE] = device
    hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE] = dict()

    scan_interval = timedelta(
        seconds=DEFAULT_SCAN_INTERVAL
    )

    async def update(event_time_utc: datetime):
        hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE][SESSY_CACHE_POWER_STATUS] = await device.get_power_status()
    
    await update(dt_util.utcnow())
    hass.data[DOMAIN][config_entry.entry_id][SESSY_POLL_LISTENER] = async_track_time_interval(hass, update, scan_interval)

    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, platform)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):

        if entry.entry_id in hass.data[DOMAIN]:
            hass.data[DOMAIN].pop(entry.entry_id)
            
    return unload_ok
