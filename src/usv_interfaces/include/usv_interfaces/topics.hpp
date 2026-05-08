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
    constexpr char TOPIC_SENSOR_RADAR_NAV_SECTOR[] = "/sensors/radar/nav/sector"; // marine_sensor_msgs/RadarSector

    // 系统状态话题 (System State Topics)
    constexpr char TOPIC_MODEL_POSE[]        = "/model/wamv/pose";           // tf2_msgs/TFMessage
    /// Gazebo 侧 `/model/{model}/odometry`（桥接 yaml 中 gz_topic_name）
    constexpr char TOPIC_MODEL_ODOMETRY[]    = "/model/wamv/odometry";       // nav_msgs/Odometry (经桥接)
    /// 集成 usv_sim_full：桥接后的 ROS 话题 `/{robot_name}/odom`
    constexpr char TEMPLATE_ROBOT_ODOM[]     = "/{robot_name}/odom";
    constexpr char TOPIC_MODEL_JOINT_STATE[] = "/model/wamv/joint_state";    // sensor_msgs/JointState
    constexpr char TOPIC_JOINT_STATES[]      = "/joint_states";              // sensor_msgs/JointState
    constexpr char TOPIC_TF[]                = "/tf";                        // tf2_msgs/TFMessage
    constexpr char TOPIC_TF_STATIC[]         = "/tf_static";                 // tf2_msgs/TFMessage

    // 控制话题 (Control Topics)
    constexpr char TOPIC_CMD_VEL[]           = "/cmd_vel";                   // geometry_msgs/Twist
    constexpr char TOPIC_CMD_THRUSTER[]      = "/wamv/thrusters/left_thrust/cmd_thrust"; // Float64MultiArray
    constexpr char TOPIC_CMD_THRUSTER_RIGHT[] = "/wamv/thrusters/right_thrust/cmd_thrust"; // Float64MultiArray

    // 状态与控制 (State & Control) - 自定义话题
    constexpr char TOPIC_VESSEL_STATE[]      = "/usv/state/vessel";          // TOPIC_VESSEL_STATE: usv_interfaces/VesselState
    constexpr char TOPIC_CONTROL_DEVIATION[] = "/usv/control/deviation";     // TOPIC_CONTROL_DEVIATION: usv_interfaces/ControlDeviation
    constexpr char TOPIC_AUTOPILOT_STATE[]   = "/usv/state/autopilot";       // TOPIC_AUTOPILOT_STATE: mavros_msgs/State
    constexpr char TOPIC_STATE_VELOCITY[]    = "/usv/state/velocity";        // TOPIC_STATE_VELOCITY: geometry_msgs/TwistStamped
    constexpr char TOPIC_CONTROL_MANUAL_RAW[] = "/usv/control/manual/raw";   // TOPIC_CONTROL_MANUAL_RAW: geometry_msgs/Twist
    constexpr char TOPIC_JETSON_STATUS[]     = "/usv/monitor/jetson_status"; // TOPIC_JETSON_STATUS: usv_interfaces/JetsonStatus
    constexpr char TOPIC_HEARTBEAT[]         = "/usv/monitor/heartbeat";     // TOPIC_HEARTBEAT: usv_interfaces/HeartbeatStatus
    constexpr char TOPIC_TASK_PROGRESS[]     = "/usv/task/progress";         // TOPIC_TASK_PROGRESS: usv_interfaces/TaskProgress
    constexpr char ACTION_EXECUTE_AUTO_TASK[] = "/usv/task/execute_auto_task"; // ACTION_EXECUTE_AUTO_TASK: usv_interfaces/action/ExecuteAutoTask
    constexpr char TOPIC_MAVROS_STATE_RAW[]  = "/mavros/state";              // TOPIC_MAVROS_STATE_RAW: mavros_msgs/State
    constexpr char SERVICE_AUTOPILOT_CONTROL[] = "/usv/control/autopilot";   // SERVICE_AUTOPILOT_CONTROL: usv_interfaces/srv/AutopilotControl
    constexpr char SERVICE_ESTOP[]           = "/usv/service/estop";         // SERVICE_ESTOP: usv_interfaces/srv/EStop
    constexpr char SERVICE_ARM[]             = "/usv/service/arm";           // SERVICE_ARM: usv_interfaces/srv/Arm
    constexpr char SERVICE_SET_MODE[]        = "/usv/service/set_mode";      // SERVICE_SET_MODE: usv_interfaces/srv/SetMode
    constexpr char SERVICE_MANUAL_CONTROL[]  = "/usv/service/manual_control"; // SERVICE_MANUAL_CONTROL: usv_interfaces/srv/ManualControl
    constexpr char SERVICE_SET_PARAMS[]      = "/usv/service/set_params";    // SERVICE_SET_PARAMS: usv_interfaces/srv/SetParams
    constexpr char SERVICE_IO_CONTROL[]      = "/usv/service/io_control";    // SERVICE_IO_CONTROL: usv_interfaces/srv/IoControl
    constexpr char SERVICE_DIAG_REQUEST[]    = "/usv/service/diag_request";  // SERVICE_DIAG_REQUEST: usv_interfaces/srv/DiagRequest
    constexpr char SERVICE_VIDEO_CONTROL[]   = "/usv/service/video_control"; // SERVICE_VIDEO_CONTROL: usv_interfaces/srv/VideoControl
    constexpr char SERVICE_RADAR_NAV_CONFIG[] = "/usv/service/radar_nav_config"; // SERVICE_RADAR_NAV_CONFIG: usv_interfaces/srv/RadarNavConfig

    // 动态传感器话题模板 (Dynamic Sensor Topic Templates)
    constexpr char TEMPLATE_CAMERA[] = "/sensors/camera/{sensor_name}/image_raw";
    constexpr char TEMPLATE_LIDAR[]  = "/sensors/lidar/{sensor_name}/points";
    constexpr char TEMPLATE_MMWAVE_POINTS[] = "/sensors/mmwave/{sensor_name}/points";
    constexpr char TEMPLATE_GPS[]    = "/sensors/gps/{sensor_name}/fix";
    constexpr char TEMPLATE_IMU[]    = "/sensors/imu/{sensor_name}/data";

    /// Gazebo FourDRadarPlugin 直发 ROS（与 full_config mmwave_front 默认 override 对齐）
    constexpr char TOPIC_SENSOR_MMWAVE_FRONT_POINTS[] = "/sensors/mmwave/mmwave_front/points";

    // NavRadar and other missing constants for gy_radar_driver
    constexpr char IP_NAVRADAR[]       = "192.168.0.71";
    constexpr char IP_AIS[]            = "192.168.254.50";
    constexpr int PORT_NAVRADAR        = 30842;
    constexpr int PORT_AIS             = 22222;

    constexpr char FRAME_NAVRADAR[]    = "nav_radar_link";

    constexpr char TOPIC_SENSOR_MMW_RAW[]    = "/sensors/radar/mmw/points";
    constexpr char TOPIC_SENSOR_NAV_SECTOR[] = "/sensors/radar/nav/sector";
    constexpr char TOPIC_SENSOR_NAV_POINTS[] = "/sensors/radar/nav/points";
    
    constexpr char TOPIC_PERCEPTION_MMW[]    = "/perception/radar/mmw/objects";
    constexpr char TOPIC_PERCEPTION_NAV[]    = "/perception/radar/nav/objects";
    constexpr char TOPIC_PERCEPTION_NAV_FRAME[] = "/perception/radar/nav/objects_frame";
    constexpr char TOPIC_PERCEPTION_VISUAL[] = "/perception/camera/objects";
    
    constexpr char TOPIC_MAP_NAVRADAR_GRIDMAP[]    = "/map/navradar/gridmap";
    constexpr char TOPIC_MAP_NAVRADAR_OUUCPANCYGRID[]    = "/map/navradar/occupancy_grid";
    constexpr char TOPIC_MAP_ENC[]    = "/map/s57_data";

} // namespace usv_interfaces

#endif // USV_INTERFACES__TOPICS_HPP_
