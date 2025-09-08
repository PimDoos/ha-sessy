"""Sensor to read data from Sessy"""
from __future__ import annotations
from datetime import datetime, timedelta

from homeassistant.const import (
    CURRENCY_EURO,
    UnitOfPower,
    PERCENTAGE,
    UnitOfElectricPotential,
    UnitOfElectricCurrent,
    UnitOfInformation,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfFrequency,
    UnitOfEnergy,
    UnitOfVolume
)
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.event import async_track_time_change

from sessypy.const import SessySystemState, SessyP1State
from sessypy.devices import SessyBattery, SessyP1Meter, SessyCTMeter

from typing import Callable, Optional

from .coordinator import SessyCoordinator, SessyCoordinatorEntity
from .models import SessyConfigEntry
from .util import (divide_by_hundred_thousand, enum_to_options_list, get_nested_key, status_string_p1, status_string_system_state, transform_on_list, 
                   unit_interval_to_percentage, divide_by_thousand, only_negative_as_positive, only_positive)

import logging
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: SessyConfigEntry, async_add_entities):
    """Set up the Sessy sensors"""

    device = config_entry.runtime_data.device
    coordinators = config_entry.runtime_data.coordinators
    sensors = []

    try:
        # Disable WiFi RSSI sensor if WiFi is not connected on discovery
        network_status_coordinator: SessyCoordinator = coordinators[device.get_network_status]
        network_status: dict = network_status_coordinator.raw_data

        if get_nested_key(network_status,"wifi_sta.rssi") is not None:
            sensors.append(
                SessySensor(hass, config_entry, "WiFi RSSI",
                            network_status_coordinator, "wifi_sta.rssi",
                            SensorDeviceClass.SIGNAL_STRENGTH, SensorStateClass.MEASUREMENT, SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
                            entity_category=EntityCategory.DIAGNOSTIC)
            )
    except Exception as e:
        _LOGGER.warning(f"Error setting up WiFi RSSI sensor: {e}")


    for memory_type in ("internal","external"):
        sensors.append(
            SessySensor(hass, config_entry, f"{ memory_type.title() } Memory Available",
                        coordinators[device.get_system_info], f"{ memory_type }_mem_available",
                        SensorDeviceClass.DATA_SIZE, SensorStateClass.MEASUREMENT, UnitOfInformation.BYTES,
                        entity_category=EntityCategory.DIAGNOSTIC)

        )

    if isinstance(device, SessyBattery):

        # Dynamic Schedule
        try:
            # Disable sensors if no schedule is present on discovery
            dynamic_schedule_coordinator: SessyCoordinator = coordinators.get(device.get_dynamic_schedule, None)
            if dynamic_schedule_coordinator is not None:
                dynamic_schedule: dict = dynamic_schedule_coordinator.raw_data

                if dynamic_schedule.get("dynamic_schedule", None) is not None:
                    sensors.append(
                        SessyScheduleSensor(hass, config_entry, "Power Schedule",
                                    dynamic_schedule_coordinator, "dynamic_schedule",
                                    SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT,
                                    schedule_key="power"
                        )
                    )

                if dynamic_schedule.get("energy_prices", None) is not None:
                    sensors.append(
                        SessyScheduleSensor(hass, config_entry, "Energy Price",
                                    dynamic_schedule_coordinator, "energy_prices",
                                    None, SensorStateClass.MEASUREMENT, f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
                                    schedule_key="price", transform_function=divide_by_hundred_thousand                
                        )
                    )
            else:
                # Fallback to legacy schedule if dynamic schedule is not supported
                # TODO remove this when legacy schedule is no longer supported

                dynamic_schedule_coordinator: SessyCoordinator = coordinators.get(device.get_dynamic_schedule_legacy, None)
                if dynamic_schedule_coordinator is not None:
                    dynamic_schedule: dict = dynamic_schedule_coordinator.raw_data

                    if dynamic_schedule.get("power_strategy", None) is not None:
                        sensors.append(
                            SessyLegacyScheduleSensor(hass, config_entry, "Power Schedule",
                                dynamic_schedule_coordinator, "power_strategy",
                                SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT,
                                schedule_key="power"
                            )
                        )

                    if dynamic_schedule.get("energy_prices", None) is not None:
                        sensors.append(
                            SessyLegacyScheduleSensor(hass, config_entry, "Energy Price",
                                        dynamic_schedule_coordinator, "energy_prices",
                                        None, SensorStateClass.MEASUREMENT, f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
                                        schedule_key="price", transform_function=divide_by_hundred_thousand            
                            )
                        )

        except Exception as e:
            _LOGGER.warning(f"Error setting up schedule sensors: {e}")


        # Power Status
        try:
            power_status_coordinator: SessyCoordinator = coordinators[device.get_power_status]
            power_status: dict = power_status_coordinator.raw_data

            sensors.append(
                SessySensor(hass, config_entry, "System State",
                            power_status_coordinator, "sessy.system_state",
                            SensorDeviceClass.ENUM,
                            translation_key = "battery_system_state", transform_function=status_string_system_state,
                            options = enum_to_options_list(SessySystemState, status_string_system_state))
            )
            sensors.append(
                SessySensor(hass, config_entry, "System State Details",
                            power_status_coordinator, "sessy.system_state_details",
                            entity_category=EntityCategory.DIAGNOSTIC)
            )
            sensors.append(
                SessySensor(hass, config_entry, "State of Charge",
                            power_status_coordinator, "sessy.state_of_charge",
                            SensorDeviceClass.BATTERY, SensorStateClass.MEASUREMENT, PERCENTAGE,
                            transform_function=unit_interval_to_percentage, precision = 1)
            )
            sensors.append(
                SessySensor(hass, config_entry, "Power",
                            power_status_coordinator, "sessy.power",
                            SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT)
            )
            sensors.append(
                SessySensor(hass, config_entry, "Charge Power",
                            power_status_coordinator, "sessy.power",
                            SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT,
                            transform_function=only_negative_as_positive)
            )
            sensors.append(
                SessySensor(hass, config_entry, "Discharge Power",
                            power_status_coordinator, "sessy.power",
                            SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT,
                            transform_function=only_positive)
            )
            sensors.append(
                SessySensor(hass, config_entry, "Frequency",
                            power_status_coordinator, "sessy.frequency",
                            SensorDeviceClass.FREQUENCY, SensorStateClass.MEASUREMENT, UnitOfFrequency.HERTZ,
                            transform_function=divide_by_thousand, precision = 3)
            )

        
            if get_nested_key(power_status, "sessy.inverter_current_ma") is not None:
                sensors.append(
                    SessySensor(hass, config_entry, "Inverter Current",
                                power_status_coordinator, "sessy.inverter_current_ma",
                                SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, UnitOfElectricCurrent.MILLIAMPERE,
                                suggested_unit_of_measurement=UnitOfElectricCurrent.AMPERE)
                )

            if get_nested_key(power_status, "sessy.pack_voltage") is not None:
                sensors.append(
                    SessySensor(hass, config_entry, "Pack Voltage",
                                power_status_coordinator, "sessy.pack_voltage",
                                SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, UnitOfElectricPotential.MILLIVOLT,
                                suggested_unit_of_measurement=UnitOfElectricPotential.VOLT)
                )
                
            if get_nested_key(power_status, "sessy.external_power") is not None:
                sensors.append(
                    SessySensor(hass, config_entry, "External Power",
                                power_status_coordinator, "sessy.external_power",
                                SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT)
                )

        except Exception as e:
            _LOGGER.warning(f"Error setting up power status sensors: {e}")


        # Sessy Energy sensors
        try:
            # Fetch API content to check compatibility
            energy_status_coordinator: SessyCoordinator = coordinators[device.get_energy_status]
            energy_status: dict = energy_status_coordinator.raw_data
            if energy_status is not None:
                sensors.append(
                    SessySensor(hass, config_entry, "Charged Energy",
                                energy_status_coordinator, "sessy_energy.import_wh",
                                SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.WATT_HOUR, 
                                suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR)
                )
                sensors.append(
                    SessySensor(hass, config_entry, "Discharged Energy",
                                energy_status_coordinator, "sessy_energy.export_wh",
                                SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.WATT_HOUR, 
                                suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR)
                )
        except Exception as e:
            _LOGGER.warning(f"Error setting up battery energy sensors: {e}")
        
        for phase_id in range(1,4):
            sensors.append(
                SessySensor(hass, config_entry, f"Renewable Energy Phase { phase_id } Voltage",
                            power_status_coordinator, f"renewable_energy_phase{ phase_id }.voltage_rms",
                            SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, UnitOfElectricPotential.MILLIVOLT,
                            suggested_unit_of_measurement=UnitOfElectricPotential.VOLT)
            )
            sensors.append(
                SessySensor(hass, config_entry, f"Renewable Energy Phase { phase_id } Current",
                            power_status_coordinator, f"renewable_energy_phase{ phase_id }.current_rms",
                            SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, UnitOfElectricCurrent.MILLIAMPERE,
                            suggested_unit_of_measurement=UnitOfElectricCurrent.AMPERE)
            )
            sensors.append(
                SessySensor(hass, config_entry, f"Renewable Energy Phase { phase_id } Power",
                            power_status_coordinator, f"renewable_energy_phase{ phase_id }.power",
                            SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT)
            )

            # Metered phase energy sensors
            try:
                if energy_status is not None:
                    sensors.append(
                        SessySensor(hass, config_entry, f"Renewable Energy Phase { phase_id } Imported Energy",
                                    energy_status_coordinator, f"energy_phase{ phase_id }.import_wh",
                                    SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.WATT_HOUR, 
                                    suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR)
                    )
                    sensors.append(
                        SessySensor(hass, config_entry, f"Renewable Energy Phase { phase_id } Exported Energy",
                                    energy_status_coordinator, f"energy_phase{ phase_id }.export_wh",
                                    SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.WATT_HOUR, 
                                    suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR)
                    )
            except Exception as e:
                _LOGGER.warning(f"Error setting up battery metered phase energy sensors: {e}")


    elif isinstance(device, SessyP1Meter):
        p1_details_coordinator: SessyCoordinator = coordinators[device.get_p1_details]
        sensors.append(
            SessySensor(hass, config_entry, "P1 Status",
                        p1_details_coordinator, "state",
                        SensorDeviceClass.ENUM,
                        translation_key = "p1_state", transform_function=status_string_p1,
                        options = enum_to_options_list(SessyP1State, status_string_p1)
                        )
        )
        sensors.append(
            SessySensor(hass, config_entry, "Tariff",
                        p1_details_coordinator, "tariff_indicator")
        )

        sensors.append(
            SessySensor(hass, config_entry, "P1 Power",
                        p1_details_coordinator, "power_total",
                        SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT)
        )
        sensors.append(
            SessySensor(hass, config_entry, "P1 Consuming Power",
                        p1_details_coordinator, "power_consumed",
                        SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT)
        )
        sensors.append(
            SessySensor(hass, config_entry, "P1 Producing Power",
                        p1_details_coordinator, "power_produced",
                        SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT)
        )
        try:
            p1_details: dict = p1_details_coordinator.raw_data
            gas_meter_present = p1_details.get("gas_meter_value", 0) != 0
            sensors.append(
                SessySensor(hass, config_entry, "Gas Consumption",
                            p1_details_coordinator, "gas_meter_value",
                            SensorDeviceClass.GAS, SensorStateClass.TOTAL, UnitOfVolume.CUBIC_METERS, 
                            transform_function=divide_by_thousand, precision = 3, enabled_default = gas_meter_present)
            )
        except Exception as e:
            _LOGGER.warning(f"Error setting up gas meter: {e}")

        
        for phase_id in range(1,4):
            sensors.append(
                SessySensor(hass, config_entry, f"Phase { phase_id } Voltage",
                            p1_details_coordinator, f"voltage_l{ phase_id }",
                            SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, UnitOfElectricPotential.MILLIVOLT,
                            suggested_unit_of_measurement=UnitOfElectricPotential.VOLT)
            )
            sensors.append(
                SessySensor(hass, config_entry, f"Phase { phase_id } Current",
                            p1_details_coordinator, f"current_l{ phase_id }",
                            SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, UnitOfElectricCurrent.MILLIAMPERE, precision = 0,
                            suggested_unit_of_measurement=UnitOfElectricCurrent.AMPERE)
            )
            sensors.append(
            SessySensor(hass, config_entry, f"Phase { phase_id } Consuming Power",
                        p1_details_coordinator, f"power_consumed_l{ phase_id }",
                        SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT)
            )
            sensors.append(
                SessySensor(hass, config_entry, f"Phase { phase_id } Producing Power",
                            p1_details_coordinator, f"power_produced_l{ phase_id }",
                            SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT)
            )

        for tariff_id in range(1,3):
            sensors.append(
                SessySensor(hass, config_entry, f"Tariff { tariff_id } Consumed Energy",
                            p1_details_coordinator, f"power_consumed_tariff{ tariff_id }",
                            SensorDeviceClass.ENERGY, SensorStateClass.TOTAL, UnitOfEnergy.WATT_HOUR, 
                            suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR)
            )
            sensors.append(
                SessySensor(hass, config_entry, f"Tariff { tariff_id } Produced Energy",
                            p1_details_coordinator, f"power_produced_tariff{ tariff_id }",
                            SensorDeviceClass.ENERGY, SensorStateClass.TOTAL, UnitOfEnergy.WATT_HOUR, 
                            suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR)
            )


    elif isinstance(device, SessyCTMeter):
        ct_details_coordinator: SessyCoordinator = coordinators[device.get_ct_details]
        sensors.append(
            SessySensor(hass, config_entry, "Total Power",
                        ct_details_coordinator, "total_power",
                        SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT)
        )
        for phase_id in range(1,4):
            sensors.append(
                SessySensor(hass, config_entry, f"Phase { phase_id } Voltage",
                            ct_details_coordinator, f"voltage_l{ phase_id }",
                            SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, UnitOfElectricPotential.MILLIVOLT, precision = 3,
                            suggested_unit_of_measurement=UnitOfElectricPotential.VOLT)
            )
            sensors.append(
                SessySensor(hass, config_entry, f"Phase { phase_id } Current",
                            ct_details_coordinator, f"current_l{ phase_id }",
                            SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, UnitOfElectricCurrent.MILLIAMPERE, precision = 3,
                            suggested_unit_of_measurement=UnitOfElectricCurrent.AMPERE)
            )
            sensors.append(
                SessySensor(hass, config_entry, f"Phase { phase_id } Power",
                            ct_details_coordinator, f"power_l{ phase_id }",
                            SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT)
            )

            # Metered phase energy sensors
            try:
                # Fetch API content to check compatibility
                energy_status_coordinator: SessyCoordinator = coordinators[device.get_energy_status]
                energy_status: dict = energy_status_coordinator.raw_data
                if energy_status is not None:
                    sensors.append(
                        SessySensor(hass, config_entry, f"Phase { phase_id } Imported Energy",
                                    energy_status_coordinator, f"energy_phase{ phase_id }.import_wh",
                                    SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.WATT_HOUR, 
                                    suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR)
                    )
                    sensors.append(
                        SessySensor(hass, config_entry, f"Phase { phase_id } Exported Energy",
                                    energy_status_coordinator, f"energy_phase{ phase_id }.export_wh",
                                    SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.WATT_HOUR, 
                                    suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR)
                    )
            except Exception as e:
                _LOGGER.warning(f"Error setting up CT meter energy sensors: {e}")

    async_add_entities(sensors)

class SessySensor(SessyCoordinatorEntity, SensorEntity):
    def __init__(self, hass: HomeAssistant, config_entry: SessyConfigEntry, name: str,
                 coordinator: SessyCoordinator, data_key,
                 device_class: SensorDeviceClass = None, state_class: SensorStateClass = None, unit_of_measurement = None,
                 transform_function: Optional[Callable] = None, translation_key: str = None,
                 options = None, entity_category: EntityCategory = None, precision: int = None, 
                 suggested_unit_of_measurement = None, enabled_default: bool = True):

        super().__init__(hass=hass, config_entry=config_entry, name=name,
                       coordinator=coordinator, data_key=data_key,
                       transform_function=transform_function, translation_key=translation_key)

        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_entity_category = entity_category

        self._attr_suggested_display_precision = precision
        self._attr_suggested_unit_of_measurement = suggested_unit_of_measurement

        self._attr_options = options

        self._attr_entity_registry_enabled_default = enabled_default

    def update_from_cache(self):
        self._attr_available = self.cache_value is not None
        self._attr_native_value = self.cache_value

class SessyScheduleSensor(SessySensor):

    def __init__(self, hass: HomeAssistant, config_entry: SessyConfigEntry, name: str,
                 coordinator: SessyCoordinator, data_key,
                 device_class: SensorDeviceClass = None, state_class: SensorStateClass = None, unit_of_measurement = None,
                 transform_function: Optional[Callable] = None, schedule_key: str = None,
                 precision: int = None, enabled_default: bool = True):

        self.schedule_transform_function = transform_function
        super().__init__(hass=hass, config_entry=config_entry, name=name,
                       coordinator=coordinator, data_key=data_key,
                       transform_function=None,
                       device_class=device_class, state_class=state_class, unit_of_measurement=unit_of_measurement,
                       precision=precision, enabled_default=enabled_default)
        
        self.schedule_key = schedule_key

        async def update_schedule(event_time_utc: datetime = None):
            self.update_from_cache()
            self.async_write_ha_state()

        # Update on top of hour
        self.tracker = async_track_time_change(hass, update_schedule, None, 0, 0)
        
    def update_from_cache(self):
        now = datetime.now()

        schedule: list = self.cache_value

        schedule_entries_now = list(
            filter(
                lambda i: i.get('start_time') <= now.timestamp()
                and i.get('end_time') > now.timestamp(), schedule
            )
        )

        current_schedule_entry = schedule_entries_now.pop(0) if len(schedule_entries_now) > 0 else None
        if current_schedule_entry is None:
            current_value = None
        else:
            current_value = current_schedule_entry.get(self.schedule_key, None)

        
        if self.schedule_transform_function:
            current_value = self.schedule_transform_function(
                current_value
            )
        
        self._attr_native_value = current_value
        self._attr_available = self._attr_native_value is not None

        self._attr_extra_state_attributes = {}

        schedule_entry: dict

        prices_attribute = dict()

        for schedule_entry in schedule:
            start_date = datetime.fromtimestamp(schedule_entry.get("start_time"))
            if self.schedule_transform_function:
                prices_attribute[start_date] = self.schedule_transform_function(
                    schedule_entry.get(self.schedule_key)
                )
            else:
                prices_attribute[start_date] = schedule_entry.get(self.schedule_key)

        self._attr_extra_state_attributes[self.data_key] = prices_attribute

class SessyLegacyScheduleSensor(SessySensor):

    def __init__(self, hass: HomeAssistant, config_entry: SessyConfigEntry, name: str,
                 coordinator: SessyCoordinator, data_key,
                 device_class: SensorDeviceClass = None, state_class: SensorStateClass = None, unit_of_measurement = None,
                 transform_function: Optional[Callable] = None, schedule_key: str = None,
                 precision: int = None, enabled_default: bool = True):

        self.schedule_transform_function = transform_function
        super().__init__(hass=hass, config_entry=config_entry, name=name,
                       coordinator=coordinator, data_key=data_key,
                       transform_function=None,
                       device_class=device_class, state_class=state_class, unit_of_measurement=unit_of_measurement,
                       precision=precision, enabled_default=enabled_default)
        
        self.schedule_key = schedule_key

        async def update_schedule(event_time_utc: datetime = None):
            self.update_from_cache()
            self.async_write_ha_state()

        # Update on top of hour
        self.tracker = async_track_time_change(hass, update_schedule, None, 0, 0)
        
    def update_from_cache(self):
        now = datetime.now()

        schedule_today = self.day_schedule()
        schedule_today_values = schedule_today.get(self.schedule_key, list())
        
        if self.schedule_transform_function:
            current_value = self.schedule_transform_function(
                schedule_today_values[now.hour]
            )
        else:
            current_value = schedule_today_values[now.hour]
        
        self._attr_native_value = current_value
        self._attr_available = self._attr_native_value is not None

        self._attr_extra_state_attributes = {}
        for schedule in self.cache_value:
            if self.schedule_transform_function:
                self._attr_extra_state_attributes[schedule.get("date")] = transform_on_list(
                    schedule.get(self.schedule_key),
                    self.schedule_transform_function
                )
            else:
                self._attr_extra_state_attributes[schedule.get("date")] = schedule.get(self.schedule_key)

    def day_schedule(self, offset: int = 0) -> dict:
        schedule_date = datetime.now()
        schedule_date += timedelta(days=offset)
        date_key = schedule_date.strftime("%Y-%m-%d")
        
        if len(self.cache_value) > 1:
            for day_schedule in self.cache_value:
                if day_schedule.get("date") == date_key:
                    return day_schedule
                else:
                    continue
        
        return None
