# Enum turn status
uint8 TURN_STATUS_OK = 0
uint8 TURNING_RIGHT_RATE_EXCEEDING_RANGE_NO_TI_AVAILABLE = 1
uint8 TURNING_LEFT_RATE_EXCEEDING_RANGE_NO_TI_AVAILABLE = 2
uint8 NO_TURN_INFORMATION_AVAILABLE = 3
# turn status
uint8 turn_status
# turn rate, degrees/min, + for turning right, - for turing left
float32 turn_rate