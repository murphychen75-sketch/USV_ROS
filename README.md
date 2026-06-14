# USV_ROS

ROS 2 工作区：无人水面艇（USV）实船系统主集成仓库，包含统一**接口**（`usv_interfaces`）、通信基础层（`usv_comm`），以及实船运行相关的感知 / 融合 / 监控等功能包。

`src/usv_simulation` 定位为可选仿真环境：用于 Gazebo / VRX / 仿真传感器和系统级仿真验证，不属于实船运行的必要依赖。该目录已作为 submodule 维护，远程仓库为 [`murphychen75-sketch/USV_Simulation`](https://github.com/murphychen75-sketch/USV_Simulation)，非仿真开发者克隆主仓时可不初始化该子模块。

## 支持矩阵

| 项 | 当前目标 |
|----|-----------|
| Ubuntu | 22.04 (Jammy) |
| ROS 2 | [Humble](https://docs.ros.org/en/humble/) |
| 主接口包 | `usv_interfaces` |
| 通信基础层 | `usv_comm` |
| 可选仿真环境 | `src/usv_simulation` |
| Gazebo / gz（仅仿真） | **Harmonic**（与 `ros-humble-ros-gzharmonic` 等二进制包对齐）；文档中若出现 “Garden” 多为历史表述，以本表为准 |
| 仿真入口包（仅仿真） | `usv_sim_full`（YAML 驱动） |

**已知限制**：完整仿真依赖 Gazebo gz 与 VRX 资源；`src/usv_fusion/bev/` 等体积较大，**不属于仿真最小构建集**，可按需排除。

## 文档与入口总览

| 路径 | 说明 |
|------|------|
| [docs/GIT_WORKFLOW.md](docs/GIT_WORKFLOW.md) | **协作制度**：分支、PR、验证命令、接口变更要求与 `usv_simulation` submodule 策略 |
| [docs/USV_ROS_SRC_LAYOUT.md](docs/USV_ROS_SRC_LAYOUT.md) | **源码结构**：`src/` 下各域、ROS 包边界与维护说明 |
| [src/usv_simulation/docs/docs_v3/QUICK_START.md](src/usv_simulation/docs/docs_v3/QUICK_START.md) | **用户向**：Docker / 本机环境、首次编译、**怎么跑 launch**、配置与话题 |
| [src/usv_simulation/docker/README.md](src/usv_simulation/docker/README.md) | **Docker**：Hub 镜像 `xyjy949/humble2harmonic`、Nav2 现状、**X11 + `--gpus all`** 推荐 `docker run`、容器内分步编译与验证 |
| [src/usv_simulation/README.md](src/usv_simulation/README.md) | 仿真平台说明、依赖与文档索引 |
| [src/usv_simulation/docs/docs_v3/仿真仓库结构说明.md](src/usv_simulation/docs/docs_v3/仿真仓库结构说明.md) | **架构向**：目录与包职责 |
| [src/usv_simulation/docs/docs_v3/终端输出与日志降噪.md](src/usv_simulation/docs/docs_v3/终端输出与日志降噪.md) | **实施记录**：默认降噪行为、`verbose_launch:=true` 恢复详细输出、已改文件清单 |
| [src/usv_simulation/usv_sim_full/config/notes_config.md](src/usv_simulation/usv_sim_full/config/notes_config.md) | **配置索引**：各 YAML 由谁消费、与 launch / `session_manager` 如何衔接 |
| [src/usv_interfaces/README.md](src/usv_interfaces/README.md) | 统一消息与 topic 常量 |
| [CHANGELOG.md](CHANGELOG.md) | 版本与变更记录 |
| [LICENSE](LICENSE) / [NOTICE](NOTICE) | 许可证与第三方说明 |

建议阅读顺序：**本页支持矩阵** → **GIT_WORKFLOW** → **USV_ROS_SRC_LAYOUT**。需要仿真时再阅读 **QUICK_START §0～§1**；若用容器 GUI，以 **docker/README.md** 中带 X11 与 GPU 的完整 `docker run` 为准（无 NVIDIA 或未装 Container Toolkit 时删掉 `--gpus all`）。

## 克隆与 submodule

默认只克隆主仓（实船开发）：

```bash
git clone git@github.com:murphychen75-sketch/USV_ROS.git
cd USV_ROS
```

需要仿真环境时，再初始化 `usv_simulation` 子模块：

```bash
git submodule update --init --recursive src/usv_simulation
```

首次克隆即需要完整仿真环境时：

```bash
git clone --recursive git@github.com:murphychen75-sketch/USV_ROS.git
```

## 最小构建

实船主仓基础构建以接口和通信基础层为入口：

```bash
source /opt/ros/humble/setup.bash
rosdep install --from-paths src/usv_interfaces src/usv_comm --ignore-src -r -y
./scripts/clean_build.sh --packages-select usv_interfaces usv_mqtt_bridge usv_mavlink_bridge
source install/setup.bash
```

仅接口包时：`./scripts/clean_build.sh --packages-select usv_interfaces`

## 可选仿真构建

在工作区根目录（本机或挂载为 `/workspace` 的容器内）：

```bash
source /opt/ros/humble/setup.bash
rosdep install --from-paths src/usv_interfaces src/usv_simulation --ignore-src -r -y
./scripts/clean_build.sh --packages-up-to usv_sim_full
source install/setup.bash
ros2 launch usv_sim_full main.launch.py
```

**说明**：

- 使用 **`--packages-up-to usv_sim_full`**（或等价 `colcon` 参数）会按 `usv_sim_full/package.xml` **递归编译依赖**（含海事雷达链路的 **`gy_radar_driver`、`radar_gz_bridge`** 等）。**不要**指望只执行 `colcon build --packages-select usv_sim_full` 就能跑齐 `nav2_sim_full_bringup` 等全流程（会缺包或缺 `install/<pkg>` 目录）。
- 若工作区曾在**另一台机器或宿主机**上编译过，将目录挂进容器后如出现 CMake 路径错误，先在仓库根执行 **`rm -rf build install log`** 再编。
- 全工作区粗暴安装依赖时也可用：`rosdep install --from-paths src --ignore-src -r -y`（可能解析到更多包；仿真相关依赖仍以 `usv_interfaces` + `usv_simulation` 为推荐范围）。

## Docker 要点（摘要）

- **镜像**：团队基础环境 **`xyjy949/humble2harmonic`**（Humble + Harmonic）；Hub 上 **`:latest` 默认不含 Nav2**，Nav2 仿真需在容器内 `apt install ros-humble-navigation2` 或使用仓库内 **`Dockerfile.humble2harmonic_nav2`** 构建 `:nav2` 标签（详见 **docker/README.md**）。
- **推荐 `docker run`**：`--network host`、挂载仓库根到 **`/workspace`**、`-w /workspace`；带 Gazebo/RViz 时加 **X11** 与 **`--gpus all`**（细节与备用 `Xauthority` 示例见 **docker/README.md**）。
- **宿主 `docker run` 可在任意目录执行**；`-v` 使用仓库根的**绝对路径**即可。

## 发版与标签

- 版本号与变更见 [CHANGELOG.md](CHANGELOG.md)。
- 建议标签格式：`v0.1.0`（与 `CHANGELOG` 中 **Unreleased** 转正时一致）。

## 许可证

本项目默认以 [Apache License 2.0](LICENSE) 分发；VRX、marine_msgs、foxglove-sdk 等保留各自许可证，详见 [NOTICE](NOTICE) 与 [src/usv_simulation/third_party/README.md](src/usv_simulation/third_party/README.md)。




目前已经知道的,必须的依赖包

ros-humble-nmea-navsat-driver

