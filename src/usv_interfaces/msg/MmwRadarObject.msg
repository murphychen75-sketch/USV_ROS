std_msgs/Header header
uint32 id               # 目标ID
geometry_msgs/Point position # 相对本船的位置 (x, y, z)
geometry_msgs/Vector3 velocity # 相对速度 (vx, vy, vz)
float32 range           # 距离 (m)
float32 azimuth         # 方位角 (rad)
float32 rcs             # 雷达截面积/强度
