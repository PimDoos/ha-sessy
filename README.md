# ha-sessy
[![Validate with hassfest](https://github.com/PimDoos/ha-sessy/actions/workflows/hassfest.yaml/badge.svg)](https://github.com/PimDoos/ha-sessy/actions/workflows/hassfest.yaml)
[![HACS Action](https://github.com/PimDoos/ha-sessy/actions/workflows/hacs.yaml/badge.svg)](https://github.com/PimDoos/ha-sessy/actions/workflows/hacs.yaml)

Home Assistant integration for Sessy home battery system.

Currently supported:
- Connect to Battery or P1 Dongle
- Power Status sensors
- Set power strategy (select entity)
- Set power setpoint (number entity)
- Wifi RSSI sensor (Battery only)
- P1 Status sensors (P1 Dongle only)
- Firmware updates
- Change configuration (min/max power)

TODO:
- [X] Add Power Status sensors
- [X] Add Power Strategy select
- [X] Add Power Setpoint number entity
- [X] Add update entities
- [X] Add Device Registry information
- [X] Add logo to home-assistant/brands
- [X] Add HACS configuration
- [ ] Add to HACS Default repository
- [ ] Add Energy sensors

Installation
============

HACS
----
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Add this repository to HACS via the Custom Repositories options.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=PimDoos&category=integration&repository=ha-sessy)

Manual
------
- Copy the `custom_components/sessy` folder to the `custom_components` folder in your configuration directory.

Configuration
=============
Add Sessy via the Integrations menu: 

- Go to Integrations > Add Integrations > Sessy

  [![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=sessy)

- Discovered Sessy devices will be shown in the list. Alternatively, enter the hostname (sessy-xxxx.local) manually.

- Enter the local username and password found on the sticker on the device

- The integration will discover the device type and add it to Home Assistant

