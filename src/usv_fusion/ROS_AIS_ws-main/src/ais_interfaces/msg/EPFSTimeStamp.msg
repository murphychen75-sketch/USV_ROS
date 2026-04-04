# Enum EPFS time stamp status
uint8 STATUS_NORMAL = 0
uint8 TIME_STAMP_NOT_AVAILABLE = 1
uint8 SYSTEM_MANUAL_INPUT_MODE = 2
uint8 EPFS_DEAD_RECKONING_MODE = 3
uint8 SYSTEM_INOPERATIVE = 4
# EPFS time in seconds, should be no more than 60 if status normal
uint8 timestamp_status
uint8 seconds