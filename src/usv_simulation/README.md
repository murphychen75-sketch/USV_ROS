# USV Simulation - 无人水面艇仿真平台

## 项目概述

USV Simulation 是一个基于 ROS2 和 Gazebo Harmonic 的无人水面艇仿真平台。该项目基于 VRX (Volvo Robotics Competition) 框架，专为 USV (Unmanned Surface Vehicle) 系统的开发、测试和验证而设计。

## 项目结构

```
src/usv_simulation/
├── usv_sim_full/              # 完整仿真系统
│   ├── config/                # 仿真配置文件
│   ├── launch/                # 启动文件
│   │   ├── components/        # 组件启动文件
│   │   └── main.launch.py     # 主启动文件
│   ├── logs/                  # 仿真日志和会话数据
│   ├── scripts/               # 核心脚本
│   │   ├── session_manager.py # 会话管理器
│   │   └── load_robot_description.py
│   ├── templates/             # Xacro模板文件
│   │   ├── sensor_macros.xacro # 传感器宏定义
│   │   ├── wamv_no_battery.urdf.xacro # 无电池版船体
│   │   └── custom_thrusters.xacro # 自定义推进器
│   ├── docs/                  # 文档
│   └── usv_sim_full/          # Python包
├── vrx/                       # VRX仿真包
│   ├── vrx_gz/                # VRX Gazebo仿真
│   ├── vrx_ros/               # VRX ROS接口
│   └── vrx_urdf/              # VRX URDF模型
│       ├── wamv_description/  # WAM-V机器人描述
│       ├── wamv_gazebo/       # WAM-V Gazebo配置
│       └── vrx_gazebo/        # VRX Gazebo插件
└── MODELS_MANAGEMENT.md       # 模型管理规范
```

## 核心功能

### 1. 配置驱动的仿真系统

- 通过 YAML 配置文件灵活定义机器人属性
- 支持动态传感器配置
- 可配置物理参数（质量、惯性、水动力参数等）

### 2. 模块化启动系统

- **基础设施仿真** (`infra_sim.launch.py`)：启动 Gazebo 环境和世界
- **机器人启动** (`robot_bringup.launch.py`)：加载机器人模型、传感器和桥接
- **可视化** (`visualization.launch.py`)：启动 RViz2 可视化界面

### 3. 传感器管理系统

- 支持多种传感器类型：激光雷达、摄像头、IMU、GPS
- 通过 Xacro 宏定义标准化传感器接口
- 动态生成传感器配置

### 4. 模型管理系统

- 保留 VRX 原始模型结构
- 在 `usv_sim_full/models/` 中管理自定义模型
- 支持自定义船体和传感器模型

## 使用方法

### 启动仿真

```bash
cd /path/to/your/workspace
source install/setup.bash
ros2 launch usv_sim_full main.launch.py config_path:=/path/to/your/config.yaml
```

### 配置文件说明

主要配置文件位于 [config/full_config.yaml](./usv_sim_full/config/full_config.yaml]：

```yaml
environment:
  world_name: "sydney_regatta"    # 仿真世界
  
robot:
  name: "usv_sim_full"            # 机器人名称
  xacro_template: "wamv_no_battery.urdf.xacro"  # 使用无电池船体
  thruster_config: "CUSTOM"       # 推进器配置
  spawn_pose: [0.0, 0.0, 0.5, 0.0, 0.0, 0.0]  # 初始位姿

  overrides:                      # 物理参数覆盖
    mass: 180.0                   # 质量
    inertia: [100.0, 100.0, 200.0] # 惯性矩阵
    
  buoyancy_params:               # 水动力参数
    hull_length: 4.9             # 船体长度
    hull_radius: 0.213           # 船体半径

sensors:                         # 传感器配置
  lidars:
    - name: "front_lidar"
      parent_link: "base_link"
      xyz: [0.7, 0.0, 1.8]
      rpy: [0.0, 0.0, 0.0]
      topic: "/sensors/lidar/front/points"
      enabled: true
  # ... 更多传感器配置
```

### 会话管理

系统使用 [session_manager.py](./usv_sim_full/scripts/session_manager.py) 自动管理仿真会话：

1. 读取 YAML 配置文件
2. 生成参数化的 URDF 文件
3. 创建传感器桥接配置
4. 生成 RViz 配置
5. 记录会话日志到 `logs/` 目录

## 模型管理

请参考 [MODELS_MANAGEMENT.md](./MODELS_MANAGEMENT.md) 了解详细的模型管理规范。

## 自定义模型

### 添加自定义模型

1. 将自定义模型放置在 `usv_sim_full/models/assets/` 目录下
2. 在配置文件中引用模型路径
3. 重新启动仿真

### 创建自定义传感器

1. 在 [templates/sensor_macros.xacro](./usv_sim_full/templates/sensor_macros.xacro) 中定义传感器宏
2. 在配置文件中添加传感器定义
3. 重新启动仿真

## 开发说明

### 会话日志

每次运行仿真会在 `usv_sim_full/logs/` 目录下创建带时间戳的会话文件夹，包含：
- 原始配置文件
- 参数化的 Xacro 文件
- 最终的 URDF 文件
- 传感器桥接配置
- RViz 配置文件

### 仿真流程

1. [main.launch.py](./usv_sim_full/launch/main.launch.py) 启动主流程
2. [session_manager.py](./usv_sim_full/scripts/session_manager.py) 生成配置文件
3. 加载机器人模型到 Gazebo
4. 启动传感器桥接到 ROS2
5. 启动 RViz2 可视化

## 故障排除

### 常见问题

1. **找不到模型文件**：检查 `GAZEBO_MODEL_PATH` 环境变量
2. **传感器未显示**：确认传感器配置中的父链接名称正确
3. **物理参数异常**：检查质量、惯性参数是否合理

### 调试技巧

- 查看 `logs/` 目录下的最新会话文件
- 检查生成的 URDF 文件是否包含期望的配置
- 验证传感器话题是否正常发布数据

## 许可证

请参阅具体包内的 LICENSE 文件。