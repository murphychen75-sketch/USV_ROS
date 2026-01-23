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
# 传感器话题 (Sensors)
# ==========================================
TOPIC_SENSOR_GPS        = "/sensors/gps/fix"           # Type: sensor_msgs/NavSatFix
TOPIC_SENSOR_IMU        = "/sensors/imu/data"          # Type: sensor_msgs/Imu
TOPIC_SENSOR_MMW_RAW    = "/sensors/radar/mmw/points"  # Type: sensor_msgs/PointCloud2
TOPIC_SENSOR_NAV_IMAGE  = "/sensors/radar/nav/image"   # Type: sensor_msgs/CompressedImage
TOPIC_SENSOR_CAMERA     = "/sensors/camera/image_raw"  # Type: sensor_msgs/Image

# ==========================================
# 感知结果话题 (Perception)
# ==========================================
TOPIC_PERCEPTION_MMW    = "/perception/radar/mmw/objects"    # Type: usv_interfaces/MmwRadarObject
TOPIC_PERCEPTION_NAV    = "/perception/radar/nav/objects"    # Type: usv_interfaces/NavRadarObject
TOPIC_PERCEPTION_VISUAL = "/perception/camera/objects"       # Type: usv_interfaces/VisualObject
TOPIC_PERCEPTION_AIS    = "/perception/ais/data"             # Type: usv_interfaces/AisData

# ==========================================
# 状态与控制话题 (State & Control)
# ==========================================
TOPIC_VESSEL_STATE      = "/usv/state/vessel"        # Type: usv_interfaces/VesselState
TOPIC_CONTROL_DEVIATION = "/usv/control/deviation"   # Type: usv_interfaces/ControlDeviation
TOPIC_CONTROL_MODE      = "/usv/control/mode"        # Type: usv_interfaces/OperationMode
TOPIC_CMD_VEL           = "/cmd_vel"                 # Type: geometry_msgs/Twist
