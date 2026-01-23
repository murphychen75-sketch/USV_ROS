# 原始传感器数据类型对照表

为了保持与 ROS 2 生态的兼容性，本系统中的**原始传感器数据**直接使用 ROS 2 标准消息 (`sensor_msgs`)，不进行自定义封装。

## 数据流向参考

| 数据源 | 话题名称 (Code Constant) | 消息类型 (ROS Type) | 说明 |
| :--- | :--- | :--- | :--- |
| **GPS/GNSS** | `TOPIC_SENSOR_GPS` | `sensor_msgs/NavSatFix` | 包含经纬度、海拔及协方差 |
| **IMU** | `TOPIC_SENSOR_IMU` | `sensor_msgs/Imu` | 包含四元数姿态、角速度、线加速度 |
| **毫米波雷达(Raw)** | `TOPIC_SENSOR_MMW_RAW` | `sensor_msgs/PointCloud2` | 包含 x, y, z, velocity, intensity 字段 |
| **导航雷达(Raw)** | `TOPIC_SENSOR_NAV_IMAGE` | `sensor_msgs/CompressedImage` | 极坐标回波图像 (JPEG/PNG) |
| **摄像头(Raw)** | `TOPIC_SENSOR_CAMERA` | `sensor_msgs/Image` | 原始 RGB 图像数据 |
| **2D 扫描** | - | `sensor_msgs/LaserScan` | 若有单线雷达或虚拟扫描使用此格式 |

**注意**：自定义的 `.msg` 文件（如 `MmwRadarObject.msg`）仅用于描述经过感知算法处理后的**目标结果**。
