from __future__ import annotations
from datetime import datetime, timedelta
from enum import Enum
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    Platform, CONF_USERNAME, CONF_PASSWORD, CONF_HOST, 
    ATTR_NAME, ATTR_MODEL, ATTR_SW_VERSION, ATTR_IDENTIFIERS, ATTR_CONFIGURATION_URL, ATTR_MANUFACTURER
)
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.dispatcher import async_dispatcher_send

from sessypy.const import SessyApiCommand
from sessypy.devices import SessyDevice, SessyBattery, SessyP1Meter, SessyCTMeter
from sessypy.util import SessyConnectionException


from .const import DOMAIN, SESSY_CACHE, SESSY_CACHE_TRACKERS, SESSY_CACHE_TRIGGERS, SESSY_DEVICE, SESSY_DEVICE_INFO, UPDATE_TOPIC, DEFAULT_SCAN_INTERVAL

async def add_cache_command(hass: HomeAssistant, config_entry: ConfigEntry, command: SessyApiCommand, interval: timedelta = DEFAULT_SCAN_INTERVAL):
    if not command in hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE]:
        hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE][command] = dict()

    async def update(event_time_utc: datetime = None):
        device: SessyDevice = hass.data[DOMAIN][config_entry.entry_id][SESSY_DEVICE]
        cache: dict = hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE]

        try:
            result = await device.api.get(command)
            cache[command] = result
        except:
            result = None
            cache[command] = None

        async_dispatcher_send(hass, UPDATE_TOPIC.format(command))

    if command in hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE_TRACKERS]:
        # Remove running tracker to avoid duplicates
        hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE_TRACKERS][command]()

    hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE_TRACKERS][command] = async_track_time_interval(hass, update, interval)
    hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE_TRIGGERS][command] = update
    await update()

async def clear_cache_command(hass: HomeAssistant, config_entry: ConfigEntry, command: SessyApiCommand = None):
    trackers = hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE_TRACKERS]
    if command == None:

        for tracker_command in trackers:
            tracker = trackers[tracker_command]
            tracker()
    else:
        tracker = trackers[command]
        tracker()


async def trigger_cache_update(hass: HomeAssistant, config_entry: ConfigEntry, command: SessyApiCommand):
    update = hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE_TRIGGERS][command]
    await update()

def backend_status_string(status_string: str, prefix: str = "") -> str:
    return status_string.removeprefix(prefix).lower()

def status_string_p1(status_string: str) -> str:
    return backend_status_string(status_string, "P1_")

def status_string_system_state(status_string: str) -> str:
    return backend_status_string(status_string, "SYSTEM_STATE_")

def status_string_power_strategy(status_string: str) -> str:
    return backend_status_string(status_string, "POWER_STRATEGY_")

def divide_by_thousand(input: int) -> float:
    return input / 1000

def enum_to_options_list(options: Enum, transform_function: function = None) -> list[str]:
    output = list()
    for option in options:
        value = option.value
        if transform_function:
            output.append(transform_function(option.value))
        else:
            output.append(option.value)
    return output


def unit_interval_to_percentage(input: float) -> float:
    return round(input * 100,1)

async def generate_device_info(hass: HomeAssistant, config_entry: ConfigEntry, device: SessyDevice) -> dict:
    # Generate Device Info
    device_info = dict()
    device_info[ATTR_NAME] = device.name
    device_info[ATTR_MANUFACTURER] = "Charged B.V."
    device_info[ATTR_IDENTIFIERS] = {(DOMAIN, device.serial_number)}
    device_info[ATTR_CONFIGURATION_URL] = f"http://{device.host}/"

    if isinstance(device, SessyBattery):
        device_info[ATTR_MODEL] = "Sessy Battery"
    elif isinstance(device, SessyP1Meter):
        device_info[ATTR_MODEL] = "Sessy P1 Dongle"
    elif isinstance(device, SessyCTMeter):
        device_info[ATTR_MODEL] = "Sessy CT Dongle"

    return device_info