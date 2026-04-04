builtin_interfaces/Time timestamp
uint8 msg_type
uint8 repeat
uint32 mmsi
# see R-REC-M.1371-5 3.3
uint8 ais_version
# IMO ship ID number
uint32 imo_number
string<=7 call_sign
string<=20 vessel_name
# see 3.3.2
uint8 ship_type
# meters
uint16 to_bow
uint16 to_stern
uint16 to_port
uint16 to_starboard
# position fix type
uint32 epfd_fix_type
# eta time
uint8 eta_month
uint8 eta_day
uint8 eta_hour
uint8 eta_minute
# meters, this value already converted by pyais
# 25.5 for no less than 25.5
float32 draught
string<=20 destination
# 1=Not ready(default)
bool dte