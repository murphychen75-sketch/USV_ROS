# mmw_radar

## 功能说明

`mmw_radar` 是毫米波雷达 ROS2 驱动桥接包，主要功能如下：

- 通过 UDP 组播接收雷达报文，解析点云（`0xAA80/0xAA81`）和目标列表（`0xAA90/0xAA91`）。
- 发布 ROS2 话题：
  - 点云 `sensor_msgs/msg/PointCloud2`
  - 目标列表 `sensor_msgs/msg/PointCloud2`
  - 目标框 `visualization_msgs/msg/MarkerArray`
- 订阅 `Odometry`、`TwistStamped`、`Imu`，组包 `0xAA31` 并通过 UDP 单播注入到雷达。

说明：该包不做目标检测/聚类/跟踪算法，目标列表来自雷达端协议报文解析结果。

## 包结构

- `src/ra223f_node.cpp`：主节点，协议解析、话题收发、注入逻辑。
- `src/udp_interface.*`：UDP 组播/单播 socket 封装。
- `launch/launch.py`：统一启动入口。
- `config/mmw_radar_params.yaml`：参数配置文件。

## 关键参数

| 参数名 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `run_mode` | string | `both` | 运行模式，支持 `both/a/b` |
| `multicast_ip` | string | `224.0.2.3` | 雷达组播地址（接收） |
| `multicast_port` | int | `42104` | 雷达组播端口（接收） |
| `unicast_ip` | string | `10.13.2.115` | 雷达单播地址（注入发送） |
| `unicast_port` | int | `42404` | 雷达单播端口（注入发送） |
| `multicast_interface_ip` | string | `0.0.0.0` | 加入组播使用的本机网卡 IP |
| `local_port_start` | int | `50000` | 本机单播绑定端口扫描起点 |
| `local_port_end` | int | `65535` | 本机单播绑定端口扫描终点 |
| `odom_topic` | string | `/mavros/local_position/odom` | 里程计输入话题 |
| `vehicle_speed_topic` | string | `/VCU_status/vehicle_feedback` | 车速输入话题 |
| `vehicle_speed_is_signed_longitudinal` | bool | `false` | 车速是否为带符号纵向速度 |
| `imu_topic` | string | `/imu/data` | IMU 输入话题 |
| `pointcloud_topic` | string | `/mmw_radar/pointcloud_topic` | 点云输出话题 |
| `object_topic` | string | `/mmw_radar/objectList_topic` | 目标列表输出话题 |
| `object_marker_topic` | string | `/mmw_radar/object_marker` | 目标框输出话题 |
| `frame_id` | string | `mmw_radar` | 发布消息坐标系 |

## 构建与运行

在工作区根目录执行：

```bash
colcon build --packages-select mmw_radar --symlink-install
source install/setup.bash
ros2 launch mmw_radar launch.py
```

使用自定义参数文件：

```bash
ros2 launch mmw_radar launch.py params_file:=/absolute/path/to/mmw_radar_params.yaml
```

## 校验命令

```bash
ros2 param list /mmw_radar_node
ros2 topic list | rg mmw_radar
```

## 迁移说明

`launch_pkg` 已并入当前包，建议统一使用：

```bash
ros2 launch mmw_radar launch.py
```
