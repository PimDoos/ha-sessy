from __future__ import annotations
from datetime import datetime, time, timedelta
from enum import Enum
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.dispatcher import async_dispatcher_send

from sessypy.const import SessyApiCommand
from sessypy.devices import SessyDevice, SessyBattery, SessyMeter, SessyP1Meter, SessyCTMeter

import logging
_LOGGER = logging.getLogger(__name__)

from .const import DEFAULT_SCAN_INTERVAL_POWER, DOMAIN, SCAN_INTERVAL_OTA_CHECK, SESSY_CACHE, SESSY_CACHE_INTERVAL, SESSY_CACHE_TRACKERS, SESSY_CACHE_TRIGGERS, SESSY_DEVICE, UPDATE_TOPIC, DEFAULT_SCAN_INTERVAL

async def setup_cache(hass: HomeAssistant, config_entry: ConfigEntry):
    hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE] = dict()
    hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE_TRACKERS] = dict()
    hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE_TRIGGERS] = dict()
    hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE_INTERVAL] = dict()

async def setup_cache_commands(hass, config_entry: ConfigEntry, device: SessyDevice, setup=True):

    # Skip static update intervals if updating from config flow handler
    if setup:
        # Sessy will not check for updates automatically, poll at intervals
        await setup_cache_command(hass, config_entry, SessyApiCommand.OTA_CHECK, SCAN_INTERVAL_OTA_CHECK)

        await setup_cache_command(hass, config_entry, SessyApiCommand.OTA_STATUS)
        await setup_cache_command(hass, config_entry, SessyApiCommand.SYSTEM_INFO)
        await setup_cache_command(hass, config_entry, SessyApiCommand.NETWORK_STATUS)

        if isinstance(device, SessyBattery):
            await setup_cache_command(hass, config_entry, SessyApiCommand.SYSTEM_SETTINGS)
            await setup_cache_command(hass, config_entry, SessyApiCommand.POWER_STRATEGY)


    # Get power scan interval from options flow
    scan_power_seconds = config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_POWER.seconds)
    scan_interval_power = timedelta(seconds = scan_power_seconds)

    if isinstance(device, SessyBattery):
        await setup_cache_command(hass, config_entry, SessyApiCommand.POWER_STATUS, scan_interval_power)

    elif isinstance(device, SessyP1Meter):
        await setup_cache_command(hass, config_entry, SessyApiCommand.P1_DETAILS, scan_interval_power)

    elif isinstance(device, SessyCTMeter):
        await setup_cache_command(hass, config_entry, SessyApiCommand.CT_DETAILS, scan_interval_power)
    
    if isinstance(device, SessyMeter):
        await setup_cache_command(hass, config_entry, SessyApiCommand.METER_GRID_TARGET)

async def setup_cache_command(hass: HomeAssistant, config_entry: ConfigEntry, command: SessyApiCommand, interval: timedelta = DEFAULT_SCAN_INTERVAL):
    update = set_cache_command(hass, config_entry, command, interval)
    await update()


def set_cache_command(hass: HomeAssistant, config_entry: ConfigEntry, command: SessyApiCommand, interval: timedelta = DEFAULT_SCAN_INTERVAL, skip_update: bool = False) -> function:
    if not command in hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE]:
        hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE][command] = dict()

    async def update(event_time_utc: datetime = None):
        device: SessyDevice = hass.data[DOMAIN][config_entry.entry_id][SESSY_DEVICE]
        cache: dict = hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE]

        try:
            result = await device.api.get(command)
            cache[command] = result
        except Exception as e:
            result = None
            cache[command] = None
            _LOGGER.debug(f"Updating cache for {command} failed with error {e}")

        async_dispatcher_send(hass, UPDATE_TOPIC.format(command))

    if command in hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE_TRACKERS]:
        # Remove running tracker to avoid duplicates
        hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE_TRACKERS][command]()

    hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE_TRACKERS][command] = async_track_time_interval(hass, update, interval)
    hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE_TRIGGERS][command] = update
    hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE_INTERVAL][command] = interval
    
    return update

async def clear_cache_command(hass: HomeAssistant, config_entry: ConfigEntry, command: SessyApiCommand = None):
    trackers = hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE_TRACKERS]
    if command == None:

        for tracker_command in trackers:
            tracker = trackers[tracker_command]
            tracker()
    else:
        tracker = trackers[command]
        tracker()

def get_cache_command(hass: HomeAssistant, config_entry: ConfigEntry, command: SessyApiCommand, key: str = None):
    cache: dict = hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE][command]
    if cache != None:
        return None
    if key:
        return cache.get(key)
    else:
        return cache
    
def get_cache_interval(hass: HomeAssistant, config_entry: ConfigEntry, command: SessyApiCommand):
    return hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE_INTERVAL][command]

def assert_cache_interval(hass: HomeAssistant, config_entry: ConfigEntry, command: SessyApiCommand, interval: timedelta = DEFAULT_SCAN_INTERVAL):
    current_interval = get_cache_interval(hass, config_entry, command)
    if current_interval != interval:
        _LOGGER.debug(f"Updating cache update interval for {command}")
        set_cache_command(hass, config_entry, command, interval, skip_update=True)

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

def only_negative_as_positive(input: int) -> int:
    return min(input, 0) * -1

def only_positive(input: int) -> int:
    return max(input, 0)

def time_from_string(input: str) -> time:
    return datetime.strptime(input, "%H:%M").time()

def start_time_from_string(input: str) -> time:
    return time_from_string(input.split("-")[0])

def stop_time_from_string(input: str) -> time:
    return time_from_string(input.split("-")[1])


def enum_to_options_list(options: Enum, transform_function: function = None) -> list[str]:
    output = list()
    for option in options:
        value = option.value
        if transform_function:
            output.append(transform_function(value))
        else:
            output.append(value)
    return output


def unit_interval_to_percentage(input: float) -> float:
    return round(input * 100,1)

async def generate_device_info(hass: HomeAssistant, config_entry: ConfigEntry, device: SessyDevice) -> DeviceInfo:
    
    model = "Sessy Device"
    if isinstance(device, SessyBattery):
        model = "Sessy Battery"
    elif isinstance(device, SessyP1Meter):
        model = "Sessy P1 Dongle"
    elif isinstance(device, SessyCTMeter):
        model = "Sessy CT Dongle"

    # Generate Device Info
    device_info = DeviceInfo(
        name=device.name,
        manufacturer="Charged B.V.",
        identifiers={(DOMAIN, device.serial_number)},
        configuration_url=f"http://{device.host}/",
        model=model
    )

    return device_info
