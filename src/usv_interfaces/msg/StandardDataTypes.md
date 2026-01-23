# 原始传感器数据类型对照表

为了保持与 ROS 2 生态的兼容性，本系统中的**原始传感器数据**直接使用 ROS 2 标准消息 (`sensor_msgs`)，不进行自定义封装。

## 当前仿真话题参考

| 数据源 | 话题名称 (Code Constant) | 消息类型 (ROS Type) | 说明 |
| :--- | :--- | :--- | :--- |
| **GPS/GNSS** | `TOPIC_SENSOR_GPS` | `sensor_msgs/NavSatFix` | 包含经纬度、海拔及协方差 |
| **IMU** | `TOPIC_SENSOR_IMU` | `sensor_msgs/Imu` | 包含四元数姿态、角速度、线加速度 |
| **激光雷达** | `TOPIC_SENSOR_LIDAR` | `sensor_msgs/PointCloud2` | 前激光雷达点云数据 |
| **摄像头** | `TOPIC_SENSOR_CAMERA` | `sensor_msgs/Image` | 前摄像头图像数据 |
| **摄像头内参** | `TOPIC_SENSOR_CAMERA_INFO` | `sensor_msgs/CameraInfo` | 前摄像头内参信息 |
| **里程计** | `TOPIC_MODEL_ODOMETRY` | `nav_msgs/Odometry` | WAM-V里程计数据 |
| **位姿** | `TOPIC_MODEL_POSE` | `tf2_msgs/TFMessage` | WAM-V位姿数据 |
| **关节状态** | `TOPIC_MODEL_JOINT_STATE` | `sensor_msgs/JointState` | WAM-V关节状态 |
| **坐标变换** | `TOPIC_TF` | `tf2_msgs/TFMessage` | 坐标变换 |

**注意**：自定义的 `.msg` 文件（如 `VesselState.msg`）用于描述融合后的高级状态信息。
