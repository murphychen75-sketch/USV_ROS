# 此文件与 topics.hpp 保持同步
# Python 节点使用方式: from usv_interfaces.topics import *

# ==========================================
# 坐标系名称 (Frame IDs)
# ==========================================
FRAME_BASE_LINK = "base_link"      # 船体中心
FRAME_MAP       = "map"            # 全局地图
FRAME_ODOM      = "odom"           # 里程计坐标系
FRAME_GPS       = "gps_link"
FRAME_IMU       = "imu_link"
FRAME_LIDAR     = "lidar_link"

# ==========================================
# 传感器话题 (Sensors) - 与当前仿真话题匹配
# ==========================================
TOPIC_SENSOR_GPS        = "/sensors/gps/data"           # Type: sensor_msgs/NavSatFix
TOPIC_SENSOR_IMU        = "/sensors/imu/data"           # Type: sensor_msgs/Imu
TOPIC_SENSOR_LIDAR      = "/sensors/lidar/front/points" # Type: sensor_msgs/PointCloud2
TOPIC_SENSOR_CAMERA     = "/sensors/camera/front/image_raw"  # Type: sensor_msgs/Image
TOPIC_SENSOR_CAMERA_INFO = "/sensors/camera/front/camera_info" # Type: sensor_msgs/CameraInfo

# 雷达扇区 (由 radar_gz_bridge 映射到 /sensors/radar/nav/sector)
TOPIC_SENSOR_RADAR_NAV_SECTOR = "/sensors/radar/nav/sector"  # Type: marine_sensor_msgs/RadarSector

# ==========================================
# 系统状态话题 (System State)
# ==========================================
TOPIC_MODEL_POSE        = "/model/wamv/pose"            # Type: tf2_msgs/TFMessage
TOPIC_MODEL_ODOMETRY    = "/model/wamv/odometry"        # Type: nav_msgs/Odometry
TOPIC_MODEL_JOINT_STATE = "/model/wamv/joint_state"     # Type: sensor_msgs/JointState
TOPIC_JOINT_STATES      = "/joint_states"               # Type: sensor_msgs/JointState
TOPIC_TF                = "/tf"                         # Type: tf2_msgs/TFMessage
TOPIC_TF_STATIC         = "/tf_static"                  # Type: tf2_msgs/TFMessage

# ==========================================
# 控制话题 (Control Topics)
# ==========================================
TOPIC_CMD_VEL           = "/cmd_vel"                    # Type: geometry_msgs/Twist
TOPIC_CMD_THRUSTER_LEFT  = "/wamv/thrusters/left_thrust/cmd_thrust"  # Type: std_msgs/Float64MultiArray
TOPIC_CMD_THRUSTER_RIGHT = "/wamv/thrusters/right_thrust/cmd_thrust" # Type: std_msgs/Float64MultiArray

# ==========================================
# 状态与控制话题 (State & Control) - 自定义话题
# ==========================================
TOPIC_VESSEL_STATE      = "/usv/state/vessel"           # Type: usv_interfaces/VesselState
TOPIC_CONTROL_DEVIATION = "/usv/control/deviation"      # Type: usv_interfaces/ControlDeviation
TOPIC_CONTROL_MODE      = "/usv/control/mode"           # Type: usv_interfaces/OperationMode
TOPIC_WAYPOINT_ROUTE    = "/usv/control/waypoint_route" # Type: usv_interfaces/WaypointRoute

# ==========================================
# Topic Template Mapping (For Dynamic Sensors)
# ==========================================
TEMPLATE_CAMERA = "/sensors/camera/{sensor_name}/image_raw"
TEMPLATE_LIDAR = "/sensors/lidar/{sensor_name}/points"
TEMPLATE_GPS = "/sensors/gps/{sensor_name}/fix"
TEMPLATE_IMU = "/sensors/imu/{sensor_name}/data"
