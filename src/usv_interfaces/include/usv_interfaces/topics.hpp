#ifndef USV_INTERFACES__TOPICS_HPP_
#define USV_INTERFACES__TOPICS_HPP_

namespace usv_interfaces {

    // 坐标系
    constexpr char FRAME_BASE_LINK[] = "base_link";
    constexpr char FRAME_MAP[]       = "map";
    constexpr char FRAME_ODOM[]      = "odom";
    constexpr char FRAME_GPS[]       = "gps_link";
    constexpr char FRAME_IMU[]       = "imu_link";
    constexpr char FRAME_LIDAR[]     = "lidar_link";

    // 原始传感器 (Raw Sensors) - 与当前仿真话题匹配
    constexpr char TOPIC_SENSOR_GPS[]        = "/sensors/gps/data";           // sensor_msgs/NavSatFix
    constexpr char TOPIC_SENSOR_IMU[]        = "/sensors/imu/data";          // sensor_msgs/Imu
    constexpr char TOPIC_SENSOR_LIDAR[]      = "/sensors/lidar/front/points"; // sensor_msgs/PointCloud2
    constexpr char TOPIC_SENSOR_CAMERA[]     = "/sensors/camera/front/image_raw";  // sensor_msgs/Image
    constexpr char TOPIC_SENSOR_CAMERA_INFO[] = "/sensors/camera/front/camera_info"; // sensor_msgs/CameraInfo

    // 系统状态话题 (System State Topics)
    constexpr char TOPIC_MODEL_POSE[]        = "/model/wamv/pose";           // tf2_msgs/TFMessage
    constexpr char TOPIC_MODEL_ODOMETRY[]    = "/model/wamv/odometry";       // nav_msgs/Odometry
    constexpr char TOPIC_MODEL_JOINT_STATE[] = "/model/wamv/joint_state";    // sensor_msgs/JointState
    constexpr char TOPIC_JOINT_STATES[]      = "/joint_states";              // sensor_msgs/JointState
    constexpr char TOPIC_TF[]                = "/tf";                        // tf2_msgs/TFMessage
    constexpr char TOPIC_TF_STATIC[]         = "/tf_static";                 // tf2_msgs/TFMessage

    // 控制话题 (Control Topics)
    constexpr char TOPIC_CMD_VEL[]           = "/cmd_vel";                   // geometry_msgs/Twist
    constexpr char TOPIC_CMD_THRUSTER[]      = "/wamv/thrusters/left_thrust/cmd_thrust"; // Float64MultiArray
    constexpr char TOPIC_CMD_THRUSTER_RIGHT[] = "/wamv/thrusters/right_thrust/cmd_thrust"; // Float64MultiArray

    // 状态与控制 (State & Control) - 自定义话题
    constexpr char TOPIC_VESSEL_STATE[]      = "/usv/state/vessel";          // usv_interfaces/VesselState
    constexpr char TOPIC_CONTROL_DEVIATION[] = "/usv/control/deviation";     // usv_interfaces/ControlDeviation
    constexpr char TOPIC_CONTROL_MODE[]      = "/usv/control/mode";          // usv_interfaces/OperationMode

} // namespace usv_interfaces

#endif // USV_INTERFACES__TOPICS_HPP_
