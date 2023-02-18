from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.dispatcher import async_dispatcher_send
from sessypy.const import SessyApiCommand
from sessypy.devices import SessyDevice


from .const import DOMAIN, SESSY_CACHE, SESSY_CACHE_TRACKERS, SESSY_DEVICE, UPDATE_TOPIC

async def add_cache_command(hass: HomeAssistant, config_entry: ConfigEntry, command: SessyApiCommand, interval: timedelta):
    if not command in hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE]:
        hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE][command] = dict()

    async def update(event_time_utc: datetime):
        device: SessyDevice = hass.data[DOMAIN][config_entry.entry_id][SESSY_DEVICE]
        result = await device.api.get(command)

        cache: dict = hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE]
        cache[command] = result
        
        async_dispatcher_send(hass, UPDATE_TOPIC.format(command))

    
    hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE_TRACKERS][command] = async_track_time_interval(hass, update, interval)
    await update(datetime.now())

def friendly_status_string(status_string: str) -> str:
    return status_string.removeprefix("SYSTEM_STATE_").removeprefix("POWER_STRATEGY_").replace("_"," ").title()

