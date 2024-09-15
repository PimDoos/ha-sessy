# ha-sessy
[![Validate with hassfest](https://github.com/PimDoos/ha-sessy/actions/workflows/hassfest.yaml/badge.svg)](https://github.com/PimDoos/ha-sessy/actions/workflows/hassfest.yaml)
[![HACS Action](https://github.com/PimDoos/ha-sessy/actions/workflows/hacs.yaml/badge.svg)](https://github.com/PimDoos/ha-sessy/actions/workflows/hacs.yaml)

Home Assistant integration for [Sessy](https://www.sessy.nl/product/sessy/?ref=18d60a1daf) - **S**mart **E**nergy **S**torage **Sy**stem.

Supported devices:
- Sessy Dongle (Battery)
- Sessy P1 Meter
- Sessy CT Meter

Currently supported:
- Autodiscovery
- Battery status sensors
- Battery charge/discharge sensors
- Set power strategy (select entity)
- Set power setpoint (number entity)
- Wifi RSSI sensor
- Meter sensors (voltage/current/power)
- Sessy NOM Coordinator controls (X on the meter)
- P1 energy tariff counters (P1 Dongle only)
- Firmware updates
- Change configuration (min/max power, start/stop time)
- Dynamic mode schedule per hour
- EPEX Energy prices
- Energy meters for integration with Energy Dashboard

TODO:
- [X] Add Power Status sensors
- [X] Add Power Strategy select
- [X] Add Power Setpoint number entity
- [X] Add update entities
- [X] Add Device Registry information
- [X] Add logo to home-assistant/brands
- [X] Add HACS configuration
- [X] Add to HACS Default repository
- [X] Add Energy sensors

Installation
============

HACS
----
[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)

Install this repository via [HACS](https://hacs.xyz/) (recommended):

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=PimDoos&category=integration&repository=ha-sessy)

Manual
------
Copy the `custom_components/sessy` folder to the `custom_components` folder in your configuration directory.

Configuration
=============
Add Sessy via the Integrations menu: 

- Go to Integrations > Add Integrations > Sessy

  [![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=sessy)

- Discovered Sessy devices will be shown in the list. Alternatively, enter the hostname (sessy-xxxx.local) manually.

- Enter the local username and password found on the sticker on the device

- The integration will discover the device type and add it to Home Assistant

- See [ha-sessy-examples](https://github.com/PimDoos/ha-sessy-examples/tree/main) for blueprints and configuration examples using this integration

- Add Sessy to the [Home Assistant Energy Dashboard](https://my.home-assistant.io/redirect/config_energy/)
  ![Energy going into the battery: Sessy-DXXX Charged Energy. Energy coming out of the battery: Sessy-DXXX Discharged Energy](https://github.com/user-attachments/assets/dd3d6065-7c59-48e4-9d40-453a695cb749)
