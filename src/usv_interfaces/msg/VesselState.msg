std_msgs/Header header

# === 1. 地理位置 (来源: GPS/GNSS) ===
float64 latitude            # 纬度
float64 longitude           # 经度
float32 altitude            # 海拔

# === 2. 局部运动状态 (来源: 里程计/IMU融合) ===
# 包含位置(x,y,z) 和 姿态(x,y,z,w 四元数)
geometry_msgs/Pose pose

# 包含线速度(vx, vy, vz) 和 角速度(wx, wy, wz)
geometry_msgs/Twist velocity

# === 3. 欧拉角 (方便调试与UI显示) ===
float32 roll                # 横滚 (rad)
float32 pitch               # 俯仰 (rad)
float32 yaw                 # 航向 (rad)

# === 4. 设备健康状态 ===
float32 battery_voltage     # 电池电压 (V)
float32 battery_percentage  # 电量 (%)
bool leak_detected          # 漏水报警 (True=漏水)
float32 cpu_temperature     # 核心温度 (C)
