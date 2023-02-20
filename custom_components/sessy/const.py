from datetime import timedelta
from sessypy.api import SessyApiCommand

DOMAIN = "sessy"
DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)
SESSY_DEVICE = "sessy_device"
SERIAL_NUMBER = "serial_number"
SESSY_DEVICE_INFO = "sessy_device_info"

UPDATE_TOPIC = "sessy_update_topic_{}"

TIME_TRACKER_POWER = "time_tracker_power"

SESSY_CACHE = "sessy_cache"
SESSY_CACHE_TRACKERS = "sessy_cache_trackers"
SESSY_CACHE_TRIGGERS = "sessy_cache_triggers"
