from datetime import timedelta
from sessypy.api import SessyApiCommand

DOMAIN = "sessy"
DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)
SCAN_INTERVAL_POWER = timedelta(seconds=10)
SCAN_INTERVAL_OTA = timedelta(seconds=15)
SCAN_INTERVAL_OTA_CHECK = timedelta(hours=6)

SESSY_DEVICE = "sessy_device"
SERIAL_NUMBER = "serial_number"
SESSY_DEVICE_INFO = "sessy_device_info"

UPDATE_TOPIC = "sessy_update_topic_{}"

TIME_TRACKER_POWER = "time_tracker_power"

SESSY_CACHE = "sessy_cache"
SESSY_CACHE_TRACKERS = "sessy_cache_trackers"
SESSY_CACHE_TRIGGERS = "sessy_cache_triggers"

ENTITY_ERROR_THRESHOLD = 5