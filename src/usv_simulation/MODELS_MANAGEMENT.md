# USV_ROS 项目模型管理规范

## 概述

本文档描述了 USV_ROS 项目中模型文件的组织方式和管理策略。为了有效管理仿真中的各类模型文件，我们将保留 VRX 原有结构，同时为自定义模型创建专门的管理目录。

## VRX 现有目录结构

VRX 相关的模型文件分布在以下目录中，我们保留这些目录结构不变：

### VRX Gazebo 模型 (`src/usv_simulation/vrx/vrx_gz/models/`)
```
vrx_gz/models/
├── beacon/              # 信标模型
├── cone_red/            # 红色锥形浮标
├── gate/                # 门形障碍物
├── jetty/               # 码头模型
├── lander/              # 登陆器模型
├── nps_pier/            # NPS码头
├── sensor_box/          # 传感器盒
├── stationkeeping/      # 定位保持任务模型
├── wayfinding/          # 导航任务模型
├── wave_field/          # 波浪场模型
└── wind_field/          # 风场模型
```

### VRX URDF 模型 (`src/usv_simulation/vrx/vrx_urdf/`)
```
vrx_urdf/
├── vrx_gazebo/          # VRX Gazebo插件和配置
├── wamv_description/    # WAM-V机器人描述
│   ├── hooks/           # Hook脚本
│   ├── models/          # WAM-V相关模型
│   │   ├── WAM-V-Base/
│   │   ├── engine/
│   │   └── propeller/
│   └── urdf/            # URDF定义文件
│       ├── lib/         # 库文件
│       ├── sensors/     # 传感器URDF
│       ├── propulsion.xacro  # 推进系统定义
│       └── wamv.urdf.xacro   # 主URDF文件
├── wamv_gazebo/         # WAM-V Gazebo配置
    └── models/          # WAM-V Gazebo模型
        ├── landmark/
        └── mooring_bollard/
```

## 自定义模型目录 (新建)

在 [usv_sim_full](file:///home/cczh/USV_ROS/src/usv_simulation/usv_sim_full/launch/main.launch.py) 包中创建新的 [models](file:///home/cczh/USV_ROS/src/vrx/vrx_gz/models/beacon/model.sdf) 目录用于存放团队自定义模型：

```
usv_sim_full/models/
├── assets/              # 团队自定义的核心模型（被Git跟踪）
│   ├── usv_body/
│   ├── custom_sensors/
│   └── docking_stations/
├── original/            # 原始设计模型文件（被Git跟踪）
│   └── custom_parts/
├── core/                # 核心基础模型（被Git跟踪）
│   └── basic_parts/
└── generated/           # 自动生成的模型（被Git忽略）
```

## VRX 关键文件说明

### 重要 Xacro 文件
- `src/usv_simulation/vrx/vrx_urdf/wamv_description/urdf/wamv.urdf.xacro` - WAM-V 主机器人定义
- `src/usv_simulation/vrx/vrx_urdf/wamv_description/urdf/propulsion.xacro` - 推进系统定义
- `src/usv_simulation/vrx/vrx_urdf/wamv_description/urdf/sensors/sensor_macros.xacro` - 传感器宏定义
- `src/usv_simulation/vrx/vrx_urdf/wamv_gazebo/urdf/lib/gazebo.xacro` - Gazebo仿真配置

### 重要配置文件
- `src/usv_simulation/vrx/vrx_urdf/wamv_description/models/` - 物理模型定义
- `src/usv_simulation/vrx/vrx_gazebo/config/jetty.xacro` - Jetty 配置

## 模型管理策略

### VRX 模型
- 保留原始结构，不对 VRX 内部结构做任何更改
- VRX 的更新通过上游仓库同步
- 如需修改 VRX 模型，应在 [usv_sim_full/models/original/](file:///home/cczh/USV_ROS/src/usv_simulation/usv_sim_full/launch/main.launch.py) 中创建副本

### 自定义模型
- 所有团队自定义模型均放在 `usv_sim_full/models/` 目录下
- 核心模型放在 [assets/](file:///home/cczh/USV_ROS/src/vrx/vrx_gz/models/sensor_box/assets/), [original/](file:///home/cczh/USV_ROS/src/vrx/vrx_urdf/wamv_description/urdf/original/), [core/](file:///home/cczh/USV_ROS/src/vrx/vrx_gz/models/beacon/model.config) 目录，会被 Git 跟踪
- 生成的模型放在 [generated/](file:///home/cczh/USV_ROS/src/vrx/vrx_gz/models/beacon/model.sdf) 目录，会被 Git 忽略

## 操作指南

### 添加自定义模型
1. 将团队自定义模型添加到 `src/usv_simulation/usv_sim_full/models/assets/` 目录
2. 如果需要修改 VRX 模型，复制到 `src/usv_simulation/usv_sim_full/models/original/` 并进行修改
3. 确保模型文件名具有描述性且符合命名规范

### 使用模型
1. 在仿真启动文件中，确保模型路径正确设置
2. 自定义模型使用 `$(find usv_sim_full)/models/` 路径
3. VRX 模型继续使用原路径

## Git忽略规则

根据 [.gitignore](.gitignore) 文件配置，以下规则生效：

- `!src/usv_simulation/usv_sim_full/models/assets/`: 保留自定义 assets 目录
- `!src/usv_simulation/usv_sim_full/models/original/`: 保留自定义 original 目录
- `!src/usv_simulation/usv_sim_full/models/core/`: 保留自定义 core 目录
- `src/usv_simulation/usv_sim_full/models/generated/`: 忽略 generated 目录

## 最佳实践

1. **保留原始**：不修改 VRX 原始文件，保持与上游兼容
2. **自定义分离**：将自定义模型与 VRX 模型分离管理
3. **路径一致**：确保所有模型路径在 launch 文件中正确定义
4. **文档记录**：为每个自定义模型添加说明文档
5. **版本控制**：合理使用 Git 跟踪重要模型文件