"""Sensor to read data from Sessy"""
from __future__ import annotations
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
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

from sessypy.const import SessyApiCommand, SessySystemState, SessyP1State
from sessypy.devices import SessyBattery, SessyDevice, SessyP1Meter, SessyCTMeter


from .const import DOMAIN, SESSY_DEVICE
from .util import (divide_by_hundred_thousand, enum_to_options_list, get_cache_command, status_string_p1, status_string_system_state, transform_on_list, 
                   unit_interval_to_percentage, divide_by_thousand, only_negative_as_positive, only_positive)
from .sessyentity import SessyEntity

import logging
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    """Set up the Sessy sensors"""

    device = hass.data[DOMAIN][config_entry.entry_id][SESSY_DEVICE]
    sensors = []

    try:
        # Disable WiFi RSSI sensor if WiFi is not connected on discovery
        network_status: dict = get_cache_command(hass, config_entry, SessyApiCommand.NETWORK_STATUS)
        wifi_rssi_present = network_status.get("wifi_sta", dict()).get("rssi", None) != None
        if wifi_rssi_present:
            sensors.append(
                SessySensor(hass, config_entry, "WiFi RSSI",
                            SessyApiCommand.NETWORK_STATUS, "wifi_sta.rssi",
                            SensorDeviceClass.SIGNAL_STRENGTH, SensorStateClass.MEASUREMENT, SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
                            entity_category=EntityCategory.DIAGNOSTIC)
            )
    except Exception as e:
        _LOGGER.warning(f"Error setting up WiFi RSSI sensor: {e}")


    for memory_type in ("internal","external"):
        sensors.append(
            SessySensor(hass, config_entry, f"{ memory_type.title() } Memory Available",
                        SessyApiCommand.SYSTEM_INFO, f"{ memory_type }_mem_available",
                        SensorDeviceClass.DATA_SIZE, SensorStateClass.MEASUREMENT, UnitOfInformation.BYTES,
                        entity_category=EntityCategory.DIAGNOSTIC)

        )

    if isinstance(device, SessyBattery):

        # Dynamic Schedule
        try:
            # Disable sensors if no schedule is present on discovery
            dynamic_schedule: dict = get_cache_command(hass, config_entry, SessyApiCommand.DYNAMIC_SCHEDULE)
            
            power_schedule_available = dynamic_schedule.get("power_strategy", None) != None
            if power_schedule_available:
                sensors.append(
                    SessyScheduleSensor(hass, config_entry, "Power Schedule",
                                SessyApiCommand.DYNAMIC_SCHEDULE, "power_strategy",
                                SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT,
                                schedule_key="power"
                    )
                )

            energy_prices_available = dynamic_schedule.get("energy_prices", None) != None
            if energy_prices_available:
                sensors.append(
                    SessyScheduleSensor(hass, config_entry, "Energy Price",
                                SessyApiCommand.DYNAMIC_SCHEDULE, "energy_prices",
                                None, SensorStateClass.MEASUREMENT, f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
                                schedule_key="price", transform_function=divide_by_hundred_thousand                
                    )
                )

        except Exception as e:
            _LOGGER.warning(f"Error setting up schedule sensors: {e}")


        # Power Status
        try:
            power_status: dict = get_cache_command(hass, config_entry, SessyApiCommand.POWER_STATUS)

            sensors.append(
                SessySensor(hass, config_entry, "System State",
                            SessyApiCommand.POWER_STATUS, "sessy.system_state",
                            SensorDeviceClass.ENUM,
                            translation_key = "battery_system_state", transform_function=status_string_system_state,
                            options = enum_to_options_list(SessySystemState, status_string_system_state))
            )
            sensors.append(
                SessySensor(hass, config_entry, "System State Details",
                            SessyApiCommand.POWER_STATUS, "sessy.system_state_details",
                            entity_category=EntityCategory.DIAGNOSTIC)
            )
            sensors.append(
                SessySensor(hass, config_entry, "State of Charge",
                            SessyApiCommand.POWER_STATUS, "sessy.state_of_charge",
                            SensorDeviceClass.BATTERY, SensorStateClass.MEASUREMENT, PERCENTAGE,
                            transform_function=unit_interval_to_percentage, precision = 1)
            )
            sensors.append(
                SessySensor(hass, config_entry, "Power",
                            SessyApiCommand.POWER_STATUS, "sessy.power",
                            SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT)
            )
            sensors.append(
                SessySensor(hass, config_entry, "Charge Power",
                            SessyApiCommand.POWER_STATUS, "sessy.power",
                            SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT,
                            transform_function=only_negative_as_positive)
            )
            sensors.append(
                SessySensor(hass, config_entry, "Discharge Power",
                            SessyApiCommand.POWER_STATUS, "sessy.power",
                            SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT,
                            transform_function=only_positive)
            )
            sensors.append(
                SessySensor(hass, config_entry, "Frequency",
                            SessyApiCommand.POWER_STATUS, "sessy.frequency",
                            SensorDeviceClass.FREQUENCY, SensorStateClass.MEASUREMENT, UnitOfFrequency.HERTZ,
                            transform_function=divide_by_thousand, precision = 3)
            )

        
            if power_status.get("sessy", dict()).get("inverter_current_ma"):
                sensors.append(
                    SessySensor(hass, config_entry, "Inverter Current",
                                SessyApiCommand.POWER_STATUS, "sessy.inverter_current_ma",
                                SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, UnitOfElectricCurrent.MILLIAMPERE,
                                suggested_unit_of_measurement=UnitOfElectricCurrent.AMPERE)
                )
        except Exception as e:
            _LOGGER.warning(f"Error setting up power status sensors: {e}")


        # Sessy Energy sensors
        try:
            # Fetch API content to check compatibility
            energy_status: dict = get_cache_command(hass, config_entry, SessyApiCommand.ENERGY_STATUS)
            if energy_status != None:
                sensors.append(
                    SessySensor(hass, config_entry, f"Charged Energy",
                                SessyApiCommand.ENERGY_STATUS, f"sessy_energy.import_wh",
                                SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.WATT_HOUR, 
                                suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR)
                )
                sensors.append(
                    SessySensor(hass, config_entry, f"Discharged Energy",
                                SessyApiCommand.ENERGY_STATUS, f"sessy_energy.export_wh",
                                SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.WATT_HOUR, 
                                suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR)
                )
        except Exception as e:
            _LOGGER.warning(f"Error setting up battery energy sensors: {e}")
        
        for phase_id in range(1,4):
            sensors.append(
                SessySensor(hass, config_entry, f"Renewable Energy Phase { phase_id } Voltage",
                            SessyApiCommand.POWER_STATUS, f"renewable_energy_phase{ phase_id }.voltage_rms",
                            SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, UnitOfElectricPotential.MILLIVOLT,
                            suggested_unit_of_measurement=UnitOfElectricPotential.VOLT)
            )
            sensors.append(
                SessySensor(hass, config_entry, f"Renewable Energy Phase { phase_id } Current",
                            SessyApiCommand.POWER_STATUS, f"renewable_energy_phase{ phase_id }.current_rms",
                            SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, UnitOfElectricCurrent.MILLIAMPERE,
                            suggested_unit_of_measurement=UnitOfElectricCurrent.AMPERE)
            )
            sensors.append(
                SessySensor(hass, config_entry, f"Renewable Energy Phase { phase_id } Power",
                            SessyApiCommand.POWER_STATUS, f"renewable_energy_phase{ phase_id }.power",
                            SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT)
            )

            # Metered phase energy sensors
            try:
                if energy_status != None:
                    sensors.append(
                        SessySensor(hass, config_entry, f"Renewable Energy Phase { phase_id } Imported Energy",
                                    SessyApiCommand.ENERGY_STATUS, f"energy_phase{ phase_id }.import_wh",
                                    SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.WATT_HOUR, 
                                    suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR)
                    )
                    sensors.append(
                        SessySensor(hass, config_entry, f"Renewable Energy Phase { phase_id } Exported Energy",
                                    SessyApiCommand.ENERGY_STATUS, f"energy_phase{ phase_id }.export_wh",
                                    SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.WATT_HOUR, 
                                    suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR)
                    )
            except Exception as e:
                _LOGGER.warning(f"Error setting up battery metered phase energy sensors: {e}")


    elif isinstance(device, SessyP1Meter):
        sensors.append(
            SessySensor(hass, config_entry, "P1 Status",
                        SessyApiCommand.P1_DETAILS, "state",
                        SensorDeviceClass.ENUM,
                        translation_key = "p1_state", transform_function=status_string_p1,
                        options = enum_to_options_list(SessyP1State, status_string_p1)
                        )
        )
        sensors.append(
            SessySensor(hass, config_entry, "Tariff",
                        SessyApiCommand.P1_DETAILS, "tariff_indicator")
        )

        sensors.append(
            SessySensor(hass, config_entry, "P1 Power",
                        SessyApiCommand.P1_DETAILS, "power_total",
                        SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT)
        )
        sensors.append(
            SessySensor(hass, config_entry, "P1 Consuming Power",
                        SessyApiCommand.P1_DETAILS, "power_consumed",
                        SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT)
        )
        sensors.append(
            SessySensor(hass, config_entry, "P1 Producing Power",
                        SessyApiCommand.P1_DETAILS, "power_produced",
                        SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT)
        )
        try:
            settings: dict = get_cache_command(hass, config_entry, SessyApiCommand.P1_DETAILS)
            gas_meter_present = settings.get("gas_meter_value", 0) != 0
            sensors.append(
                SessySensor(hass, config_entry, f"Gas Consumption",
                            SessyApiCommand.P1_DETAILS, f"gas_meter_value",
                            SensorDeviceClass.GAS, SensorStateClass.TOTAL, UnitOfVolume.CUBIC_METERS, 
                            transform_function=divide_by_thousand, precision = 3, enabled_default = gas_meter_present)
            )
        except Exception as e:
            _LOGGER.warning(f"Error setting up gas meter: {e}")

        
        for phase_id in range(1,4):
            sensors.append(
                SessySensor(hass, config_entry, f"Phase { phase_id } Voltage",
                            SessyApiCommand.P1_DETAILS, f"voltage_l{ phase_id }",
                            SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, UnitOfElectricPotential.MILLIVOLT,
                            suggested_unit_of_measurement=UnitOfElectricPotential.VOLT)
            )
            sensors.append(
                SessySensor(hass, config_entry, f"Phase { phase_id } Current",
                            SessyApiCommand.P1_DETAILS, f"current_l{ phase_id }",
                            SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, UnitOfElectricCurrent.MILLIAMPERE, precision = 0,
                            suggested_unit_of_measurement=UnitOfElectricCurrent.AMPERE)
            )
            sensors.append(
            SessySensor(hass, config_entry, f"Phase { phase_id } Consuming Power",
                        SessyApiCommand.P1_DETAILS, f"power_consumed_l{ phase_id }",
                        SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT)
            )
            sensors.append(
                SessySensor(hass, config_entry, f"Phase { phase_id } Producing Power",
                            SessyApiCommand.P1_DETAILS, f"power_produced_l{ phase_id }",
                            SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT)
            )

        for tariff_id in range(1,3):
            sensors.append(
                SessySensor(hass, config_entry, f"Tariff { tariff_id } Consumed Energy",
                            SessyApiCommand.P1_DETAILS, f"power_consumed_tariff{ tariff_id }",
                            SensorDeviceClass.ENERGY, SensorStateClass.TOTAL, UnitOfEnergy.WATT_HOUR, 
                            suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR)
            )
            sensors.append(
                SessySensor(hass, config_entry, f"Tariff { tariff_id } Produced Energy",
                            SessyApiCommand.P1_DETAILS, f"power_produced_tariff{ tariff_id }",
                            SensorDeviceClass.ENERGY, SensorStateClass.TOTAL, UnitOfEnergy.WATT_HOUR, 
                            suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR)
            )


    elif isinstance(device, SessyCTMeter):
        sensors.append(
            SessySensor(hass, config_entry, "Total Power",
                        SessyApiCommand.CT_DETAILS, "total_power",
                        SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT)
        )
        for phase_id in range(1,4):
            sensors.append(
                SessySensor(hass, config_entry, f"Phase { phase_id } Voltage",
                            SessyApiCommand.CT_DETAILS, f"voltage_l{ phase_id }",
                            SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, UnitOfElectricPotential.MILLIVOLT, precision = 3,
                            suggested_unit_of_measurement=UnitOfElectricPotential.VOLT)
            )
            sensors.append(
                SessySensor(hass, config_entry, f"Phase { phase_id } Current",
                            SessyApiCommand.CT_DETAILS, f"current_l{ phase_id }",
                            SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, UnitOfElectricCurrent.MILLIAMPERE, precision = 3,
                            suggested_unit_of_measurement=UnitOfElectricCurrent.AMPERE)
            )
            sensors.append(
                SessySensor(hass, config_entry, f"Phase { phase_id } Power",
                            SessyApiCommand.CT_DETAILS, f"power_l{ phase_id }",
                            SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT)
            )

            # Metered phase energy sensors
            try:
                # Fetch API content to check compatibility
                energy_status: dict = get_cache_command(hass, config_entry, SessyApiCommand.ENERGY_STATUS)
                if energy_status != None:
                    sensors.append(
                        SessySensor(hass, config_entry, f"Phase { phase_id } Imported Energy",
                                    SessyApiCommand.ENERGY_STATUS, f"energy_phase{ phase_id }.import_wh",
                                    SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.WATT_HOUR, 
                                    suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR)
                    )
                    sensors.append(
                        SessySensor(hass, config_entry, f"Phase { phase_id } Exported Energy",
                                    SessyApiCommand.ENERGY_STATUS, f"energy_phase{ phase_id }.export_wh",
                                    SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.WATT_HOUR, 
                                    suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR)
                    )
            except Exception as e:
                _LOGGER.warning(f"Error setting up CT meter energy sensors: {e}")

    async_add_entities(sensors)

class SessySensor(SessyEntity, SensorEntity):
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, name: str,
                 cache_command: SessyApiCommand, cache_key,
                 device_class: SensorDeviceClass = None, state_class: SensorStateClass = None, unit_of_measurement = None,
                 transform_function: function = None, translation_key: str = None,
                 options = None, entity_category: EntityCategory = None, precision: int = None, 
                 suggested_unit_of_measurement = None, enabled_default: bool = True):

        super().__init__(hass=hass, config_entry=config_entry, name=name,
                       cache_command=cache_command, cache_key=cache_key,
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
        self._attr_available = self.cache_value != None
        self._attr_native_value = self.cache_value

class SessyScheduleSensor(SessySensor):

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, name: str,
                 cache_command: SessyApiCommand, cache_key,
                 device_class: SensorDeviceClass = None, state_class: SensorStateClass = None, unit_of_measurement = None,
                 transform_function: function = None, schedule_key: str = None,
                 precision: int = None, enabled_default: bool = True):

        self.schedule_transform_function = transform_function
        super().__init__(hass=hass, config_entry=config_entry, name=name,
                       cache_command=cache_command, cache_key=cache_key,
                       transform_function=None,
                       device_class=device_class, state_class=state_class, unit_of_measurement=unit_of_measurement,
                       precision=precision, enabled_default=enabled_default)
        
        self.schedule_key = schedule_key
        
    def update_from_cache(self):
        now = datetime.now()

        schedule_today = self.day_schedule()
        schedule_today_values = schedule_today.get(self.schedule_key, list())
        current_value = schedule_today_values[now.hour]
        if self.schedule_transform_function:
            current_value = self.schedule_transform_function(
                schedule_today_values[now.hour]
            )

        self._attr_extra_state_attributes = {}
        for schedule in self.cache_value:
            if self.schedule_transform_function:
                self._attr_extra_state_attributes[schedule.get("date")] = transform_on_list(
                    schedule.get(self.schedule_key),
                    self.schedule_transform_function
                )
            else:
                self._attr_extra_state_attributes[schedule.get("date")] = schedule.get(self.schedule_key)

        self._attr_native_value = current_value
        self._attr_available = self._attr_native_value != None
        

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
