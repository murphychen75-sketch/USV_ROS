std_msgs/Header header
uint32 id

# === 绝对运动信息 ===
float32 sog                 # 对地速度 (m/s)
float32 cog                 # 对地航向 (rad)

# === 相对关系 ===
float32 range               # 距离本船 (m)
float32 relative_bearing    # 相对本船船头的方位角 (rad)
geometry_msgs/Point position # 在地图坐标系下的估算位置

# === 属性 ===
float32 area                # 目标面积 (m^2)
bool is_moving              # 是否运动
