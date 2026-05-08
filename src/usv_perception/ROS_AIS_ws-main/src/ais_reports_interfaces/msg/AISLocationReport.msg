builtin_interfaces/Time timestamp
uint8 msg_type
uint8 repeat
uint32 mmsi
ais_interfaces/NavigationStatus navigation_status
# turn rate degrees/min
ais_interfaces/TurnRate turn_rate
# speed on ground, knot
bool is_valid_sog
float32 sog
# location gps, + for east and north, - for west and south
bool location_accuracy
bool is_valid_longitude
float32 longitude
bool is_valid_latitude
float32 latitude
# course over ground, degrees, 0.1 precision
bool is_valid_cog
float32 cog
# true heading, degrees
bool is_valid_hdg
int16 hdg
# time stamp
ais_interfaces/EPFSTimeStamp epfs_time_stamp
# indicator for special maneuver
ais_interfaces/ManeuverIndicator maneuver_indicator
# raim flag, true for raim in use, default false
bool raim
# radio status, see 3.3.7.2.2 and 3.3.7.3.2
uint32 radio