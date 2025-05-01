"""API Data Update Coordinator for Sessy"""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging

import async_timeout

from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from sessypy.devices import SessyBattery, SessyCTMeter, SessyDevice, SessyMeter, SessyP1Meter
from sessypy.util import SessyConnectionException, SessyLoginException, SessyNotSupportedException

from .const import COORDINATOR_RETRIES, COORDINATOR_RETRY_DELAY, DEFAULT_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_POWER, ENTITY_ERROR_THRESHOLD, SCAN_INTERVAL_OTA_CHECK, SCAN_INTERVAL_SCHEDULE
from .models import SessyConfigEntry
from .util import get_nested_key

_LOGGER = logging.getLogger(__name__)

async def setup_coordinators(hass, config_entry: SessyConfigEntry, device: SessyDevice):
    
    coordinators = list()

    # Get power scan interval from options flow
    if CONF_SCAN_INTERVAL in config_entry.options:
        scan_interval_power = timedelta(seconds = config_entry.options.get(CONF_SCAN_INTERVAL))
    else: scan_interval_power = DEFAULT_SCAN_INTERVAL_POWER

    # Device independent functions
    coordinators.extend([
        SessyCoordinator(hass, config_entry, device.get_ota_status),
        SessyCoordinator(hass, config_entry, device.check_ota, SCAN_INTERVAL_OTA_CHECK), # Sessy will not check for updates automatically, poll at intervals
        SessyCoordinator(hass, config_entry, device.get_system_info),
        SessyCoordinator(hass, config_entry, device.get_network_status)
    ])
    

    if isinstance(device, SessyBattery):
        coordinators.extend([
            SessyCoordinator(hass, config_entry, device.get_dynamic_schedule, SCAN_INTERVAL_SCHEDULE),
            SessyCoordinator(hass, config_entry, device.get_power_status, scan_interval_power),
            SessyCoordinator(hass, config_entry, device.get_power_strategy),
            SessyCoordinator(hass, config_entry, device.get_system_settings),
        ])


    elif isinstance(device, SessyP1Meter):
        coordinators.append(
            SessyCoordinator(hass, config_entry, device.get_p1_details, scan_interval_power)
        )

    elif isinstance(device, SessyCTMeter):
        coordinators.append(
            SessyCoordinator(hass, config_entry, device.get_ct_details, scan_interval_power)
        )
    
    if isinstance(device, SessyMeter):
        coordinators.append(
            SessyCoordinator(hass, config_entry, device.get_grid_target)
        )

    if isinstance(device, SessyBattery) or isinstance(device, SessyCTMeter):
        coordinators.append(
            SessyCoordinator(hass, config_entry, device.get_energy_status)
        )

    coordinators_dict = dict()
    coordinator: SessyCoordinator
    for coordinator in coordinators:
        await coordinator.async_config_entry_first_refresh()
        coordinators_dict[coordinator._device_function] = coordinator
    
    return coordinators_dict

async def update_coordinator_options(hass, config_entry: SessyConfigEntry):
    device = config_entry.runtime_data.device
    update_coordinator_functions: list[function] = [
        device.get_power_status,
        device.get_ct_details,
        device.get_p1_details
    ]

    # Get power scan interval from options flow
    if CONF_SCAN_INTERVAL in config_entry.options:
        scan_interval_power = timedelta(seconds = config_entry.options.get(CONF_SCAN_INTERVAL))
    else: scan_interval_power = DEFAULT_SCAN_INTERVAL_POWER

    for coordinator in config_entry.runtime_data.coordinators:
        if coordinator._device_function in update_coordinator_functions:
            coordinator.update_interval = scan_interval_power

async def refresh_coordinators(config_entry: SessyConfigEntry):
    coordinators = config_entry.runtime_data.coordinators
    for coordinator in coordinators:
        await coordinators[coordinator].async_refresh()

class SessyCoordinator(DataUpdateCoordinator):
    """Sessy API coordinator"""

    def __init__(self, hass, config_entry, device_function: function, update_interval: timedelta | dict = DEFAULT_SCAN_INTERVAL):
        """Initialize coordinator"""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name=device_function.__name__,
            config_entry=config_entry,
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=update_interval,
            # Set always_update to `False` if the data returned from the
            # api can be compared via `__eq__` to avoid duplicate updates
            # being dispatched to listeners
            always_update=False
        )
        self._device_function = device_function
        self._raw_data = dict()

    async def _async_setup(self):
        """Set up the coordinator

        This is the place to set up your coordinator,
        or to load data, that only needs to be loaded once.

        This method will be called automatically during
        coordinator.async_config_entry_first_refresh.
        """
        await self._async_update_data()

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        for retry in range(COORDINATOR_RETRIES):
            try:
                # Note: asyncio.TimeoutError and aiohttp.ClientError are already
                # handled by the data update coordinator.
                async with async_timeout.timeout(self.update_interval.seconds / 2):
                    data = await self._device_function()

                contexts: list[SessyEntityContext] = set(self.async_contexts())
                flattened_data = dict()
                for context in contexts:
                    flattened_data[context] = context.apply(data)

                self._raw_data = data
                return flattened_data

            except SessyLoginException as err:
                # Raising ConfigEntryAuthFailed will cancel future updates
                # and start a config flow with SOURCE_REAUTH (async_step_reauth)
                raise ConfigEntryAuthFailed from err
            except SessyConnectionException as err:
                await asyncio.sleep(COORDINATOR_RETRY_DELAY)
                continue

        raise UpdateFailed(f"Error communicating with Sessy API after {COORDINATOR_RETRIES} retries: {err}")
    
    def get_data(self):
        return self.data
    
    @property
    def raw_data(self):
        return self._raw_data
    
class SessyCoordinatorEntity(CoordinatorEntity):
    """Base Sessy Entity, coordinated by SessyCoordinator"""
    def __init__(self, hass: HomeAssistant, config_entry: SessyConfigEntry, name: str,
                 coordinator: SessyCoordinator, data_key: str, transform_function: function = None, translation_key: str = None):
        self.context = SessyEntityContext(data_key, transform_function)
        super().__init__(coordinator, self.context)
        self.hass = hass
        self.config_entry = config_entry
        
        self.transform_function = transform_function
        self.data_key = data_key
        self.cache_value = None

        device: SessyDevice = config_entry.runtime_data.device

        self._attr_name = name
        self._attr_has_entity_name = True
        self._attr_unique_id = f"sessy-{ device.serial_number }-sensor-{ name.replace(' ','') }".lower() #TODO Technical dept, this will cause issues if we ever need to change entity names
        self._attr_device_info = config_entry.runtime_data.device_info
        self._attr_translation_key = translation_key

        self._update_failed_count = 0

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            self.copy_from_cache()
            self._update_failed_count = 0
        except Exception as e:
            self._update_failed_count += 1
            message = f"Updating entity '{self.name}' failed for {self._update_failed_count} consecutive attempts. Exception occured: '{ e }'"
            self.cache_value = None
            if self._update_failed_count == ENTITY_ERROR_THRESHOLD:
                # Log as warning once attempts exceed threshold
                _LOGGER.warning(message)
            else:
                _LOGGER.debug(message)

        finally:
            self.update_from_cache()
            self.async_write_ha_state()
        
    def copy_from_cache(self):
        self.cache_value = self.coordinator.data.get(self.context, None)
        if self.cache_value is None:
            raise TypeError(f"Key {self.data_key} has no value in coordinator {self.coordinator.name}")
         
    def update_from_cache(self):
        """Entity function to write the latest cache value to the proper attributes. Implemented on platform level."""
        raise NotImplementedError()

class SessyEntityContext():
    def __init__(self, data_key: str, transform_function: function):
        self.data_key = data_key
        self.transform_function = transform_function
    
    def apply(self, data):
        value = get_nested_key(data, self.data_key)
        if self.transform_function: value = self.transform_function(value)
        return value