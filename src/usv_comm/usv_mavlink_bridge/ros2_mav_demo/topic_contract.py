"""Central topic/message mapping for ros2_mav_demo.

This file is the single source of truth for:
1) primary USV topics (aligned with usv_interfaces),
2) legacy compatibility topics used by existing demo tools.
"""

from usv_interfaces import topics as usv_topics

# Primary topics aligned to usv_interfaces
PRIMARY_TOPICS = {
    "imu_in": usv_topics.TOPIC_SENSOR_IMU,
    "gps_fix_in": usv_topics.TOPIC_SENSOR_GPS,
    "velocity_in": usv_topics.TOPIC_STATE_VELOCITY,
    "manual_out": usv_topics.TOPIC_CONTROL_MANUAL_RAW,
}

# Optional legacy inputs/outputs kept for transition period
LEGACY_TOPICS = {
    "imu_in": "/imu/data",
    "gps_in": "/comm/gps",
    "gpsr_in": "/comm/gpsr",
    "manual_out": "/control/manual_control_raw",
}

# ROS message type names (for docs/logs/config inspection)
TOPIC_TYPES = {
    "imu_in": "sensor_msgs/msg/Imu",
    "gps_fix_in": "sensor_msgs/msg/NavSatFix",
    "velocity_in": "geometry_msgs/msg/TwistStamped",
    "manual_out": "geometry_msgs/msg/Twist",
}

# Default MAVLink bridge transport
MAVLINK_ENDPOINT = "udpout:127.0.0.1:14550"
MAVLINK_SOURCE_SYSTEM = 1
MAVLINK_SOURCE_COMPONENT = 1
