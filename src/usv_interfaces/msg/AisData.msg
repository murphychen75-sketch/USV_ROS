std_msgs/Header header
uint32 mmsi                 # 水上移动业务标识码

# === 时间戳 ===
builtin_interfaces/Time timestamp_utc # AIS报文原始生成时间

float64 latitude
float64 longitude
float32 sog                 # m/s
float32 cog                 # rad
float32 heading             # rad
uint8 navigational_status   # 航行状态枚举
