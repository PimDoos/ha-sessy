"""The Sessy integration."""
from __future__ import annotations
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    Platform, CONF_USERNAME, CONF_PASSWORD, CONF_HOST, 
    ATTR_NAME, ATTR_MODEL, ATTR_SW_VERSION, ATTR_IDENTIFIERS, ATTR_CONFIGURATION_URL, ATTR_MANUFACTURER
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from sessypy.devices import SessyBattery, SessyCTMeter, SessyP1Meter, get_sessy_device
from sessypy.util import SessyLoginException, SessyConnectionException, SessyNotSupportedException

from .const import DOMAIN, SERIAL_NUMBER, SESSY_CACHE, SESSY_CACHE_TRACKERS, SESSY_CACHE_TRIGGERS, SESSY_DEVICE, SESSY_DEVICE_INFO

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SELECT]


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

    hass.data[DOMAIN][config_entry.entry_id][SERIAL_NUMBER] = config_entry.data.get(CONF_USERNAME).upper()
    hass.data[DOMAIN][config_entry.entry_id][SESSY_DEVICE] = device


    # Generate Device Info
    device_info = dict()
    device_info[ATTR_NAME] = device.name
    device_info[ATTR_MANUFACTURER] = "Charged B.V."
    device_info[ATTR_IDENTIFIERS] = {(DOMAIN, device.serial_number)}
    device_info[ATTR_CONFIGURATION_URL] = f"http://{device.host}/"

    software_info = await device.get_ota_status()
    installed_version = software_info.get("self",dict()).get("installed_firmware",dict()).get("version", None)
    device_info[ATTR_SW_VERSION] = installed_version

    if isinstance(device, SessyBattery):
        device_info[ATTR_MODEL] = "Sessy Battery"
    elif isinstance(device, SessyP1Meter):
        device_info[ATTR_MODEL] = "Sessy P1 Dongle"
    elif isinstance(device, SessyCTMeter):
        device_info[ATTR_MODEL] = "Sessy P1 Dongle"

    hass.data[DOMAIN][config_entry.entry_id][SESSY_DEVICE_INFO] = device_info


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
        await hass.data[DOMAIN][entry.entry_id][SESSY_DEVICE].close()
        if entry.entry_id in hass.data[DOMAIN]:
            hass.data[DOMAIN].pop(entry.entry_id)
            
    return unload_ok
