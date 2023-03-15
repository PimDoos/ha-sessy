from __future__ import annotations

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import StateType

from sessypy.const import SessyApiCommand
from sessypy.devices import SessyDevice

from .const import DOMAIN, SESSY_CACHE, SESSY_DEVICE, SESSY_DEVICE_INFO, UPDATE_TOPIC

class SessyEntity(Entity):
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, name: str,
                 cache_command: SessyApiCommand, cache_key, transform_function: function = None, translation_key: str = None):
        self.hass = hass
        self.config_entry = config_entry
        
        self.cache = hass.data[DOMAIN][config_entry.entry_id][SESSY_CACHE][cache_command]
        self.cache_command = cache_command
        self.cache_key = cache_key
        self.cache_value = None

        self.update_topic = UPDATE_TOPIC.format(cache_command)
        self.transform_function = transform_function

        device: SessyDevice = hass.data[DOMAIN][config_entry.entry_id][SESSY_DEVICE]

        self._attr_name = f"{ name }"
        self._attr_has_entity_name = True
        self._attr_unique_id = f"sessy-{ device.serial_number }-sensor-{ name.replace(' ','') }".lower()
        self._attr_device_info = hass.data[DOMAIN][config_entry.entry_id][SESSY_DEVICE_INFO]
        self._attr_translation_key = translation_key
        

    async def async_added_to_hass(self):
        @callback
        def update():
            self.cache = self.hass.data[DOMAIN][self.config_entry.entry_id][SESSY_CACHE][self.cache_command]
            value = self.get_cache_value(self.cache_key)
            if self.transform_function:
                self.cache_value = self.transform_function(value)
            else:
                self.cache_value = value
            
            self.update_from_cache()
            self.async_write_ha_state()

        await super().async_added_to_hass()
        self.update_topic_listener = async_dispatcher_connect(
            self.hass, self.update_topic, update
        )
        update()
        self.async_on_remove(self.update_topic_listener)

    def update_from_cache(self):
        """Entity function to write the latest cache value to the proper attributes. Implemented on platform level."""
        raise NotImplementedError()
    
    @property
    def should_poll(self) -> bool:
        return False
    
    def get_cache_value(self, key):
        if self.cache == None:
            return None

        value = self.cache

        if len(value) == 0:
            return None
        else:
            node: str
            for node in key.split("."):
                if node.isdigit():
                    node = int(node)
                if value == None:
                    return None
                elif node in value:
                    value = value[node]
                    continue
                else:
                    value = None
        return value