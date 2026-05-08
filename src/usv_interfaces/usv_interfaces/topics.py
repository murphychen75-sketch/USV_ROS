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
# Gazebo 侧 /model/{name}/odometry；集成仿真桥接后的 ROS 里程计见 TEMPLATE_ROBOT_ODOM
TOPIC_MODEL_ODOMETRY    = "/model/wamv/odometry"        # Type: nav_msgs/Odometry
TEMPLATE_ROBOT_ODOM     = "/{robot_name}/odom"          # usv_sim_full session_manager 桥接输出
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
TOPIC_AUTOPILOT_STATE   = "/usv/state/autopilot"        # TOPIC_AUTOPILOT_STATE
TOPIC_STATE_VELOCITY    = "/usv/state/velocity"         # TOPIC_STATE_VELOCITY
TOPIC_CONTROL_MANUAL_RAW = "/usv/control/manual/raw"    # TOPIC_CONTROL_MANUAL_RAW
TOPIC_JETSON_STATUS     = "/usv/monitor/jetson_status"  # TOPIC_JETSON_STATUS
TOPIC_HEARTBEAT         = "/usv/monitor/heartbeat"      # TOPIC_HEARTBEAT
TOPIC_TASK_PROGRESS     = "/usv/task/progress"          # TOPIC_TASK_PROGRESS
ACTION_EXECUTE_AUTO_TASK = "/usv/task/execute_auto_task" # ACTION_EXECUTE_AUTO_TASK
TOPIC_MAVROS_STATE_RAW  = "/mavros/state"               # TOPIC_MAVROS_STATE_RAW
SERVICE_AUTOPILOT_CONTROL = "/usv/control/autopilot"    # SERVICE_AUTOPILOT_CONTROL
SERVICE_ESTOP           = "/usv/service/estop"          # SERVICE_ESTOP
SERVICE_ARM             = "/usv/service/arm"            # SERVICE_ARM
SERVICE_SET_MODE        = "/usv/service/set_mode"       # SERVICE_SET_MODE
SERVICE_MANUAL_CONTROL  = "/usv/service/manual_control" # SERVICE_MANUAL_CONTROL
SERVICE_SET_PARAMS      = "/usv/service/set_params"     # SERVICE_SET_PARAMS
SERVICE_IO_CONTROL      = "/usv/service/io_control"     # SERVICE_IO_CONTROL
SERVICE_DIAG_REQUEST    = "/usv/service/diag_request"   # SERVICE_DIAG_REQUEST
SERVICE_VIDEO_CONTROL   = "/usv/service/video_control"  # SERVICE_VIDEO_CONTROL
SERVICE_RADAR_NAV_CONFIG = "/usv/service/radar_nav_config" # SERVICE_RADAR_NAV_CONFIG

# ==========================================
# Topic Template Mapping (For Dynamic Sensors)
# ==========================================
TEMPLATE_CAMERA = "/sensors/camera/{sensor_name}/image_raw"
TEMPLATE_LIDAR = "/sensors/lidar/{sensor_name}/points"
TEMPLATE_MMWAVE_POINTS = "/sensors/mmwave/{sensor_name}/points"
TEMPLATE_GPS = "/sensors/gps/{sensor_name}/fix"
TEMPLATE_IMU = "/sensors/imu/{sensor_name}/data"

# 毫米波点云（主链路多为 gpu_ray 桥接 + usv_mmwave_sim 增强；命名与 full_config 默认一致）
TOPIC_SENSOR_MMWAVE_FRONT_POINTS = "/sensors/mmwave/mmwave_front/points"
