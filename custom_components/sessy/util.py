from __future__ import annotations
from datetime import datetime, timedelta
from enum import Enum
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.dispatcher import async_dispatcher_send
from sessypy.const import SessyApiCommand
from sessypy.devices import SessyDevice


from .const import DOMAIN, SESSY_CACHE, SESSY_CACHE_TRACKERS, SESSY_CACHE_TRIGGERS, SESSY_DEVICE, UPDATE_TOPIC

async def add_cache_command(hass: HomeAssistant, config_entry: ConfigEntry, command: SessyApiCommand, interval: timedelta):
    if not command in hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE]:
        hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE][command] = dict()

    async def update(event_time_utc: datetime = None):
        device: SessyDevice = hass.data[DOMAIN][config_entry.entry_id][SESSY_DEVICE]
        result = await device.api.get(command)

        cache: dict = hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE]
        cache[command] = result
        
        async_dispatcher_send(hass, UPDATE_TOPIC.format(command))

    
    hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE_TRACKERS][command] = async_track_time_interval(hass, update, interval)
    hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE_TRIGGERS][command] = update
    await update()
async def trigger_cache_update(hass: HomeAssistant, config_entry: ConfigEntry, command: SessyApiCommand):
    update = hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE_TRIGGERS][command]
    await update()

def friendly_status_string(status_string: str) -> str:
    return status_string.removeprefix("SYSTEM_STATE_").removeprefix("POWER_STRATEGY_").replace("_"," ").title()

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
