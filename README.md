# USV_ROS

ROS 2 工作区：无人水面艇（USV）**仿真**、统一**接口**（`usv_interfaces`），以及可选的融合 / AIS 等子工程。

## 支持矩阵（仿真主线）

| 项 | 当前目标 |
|----|-----------|
| Ubuntu | 22.04 (Jammy) |
| ROS 2 | [Humble](https://docs.ros.org/en/humble/) |
| Gazebo / gz | **Harmonic**（与 `ros-humble-ros-gzharmonic` 等二进制包对齐）；文档中若出现 “Garden” 多为历史表述，以本表为准 |
| 仿真入口包 | `usv_sim_full`（YAML 驱动） |

**已知限制**：完整仿真依赖 Gazebo gz 与 VRX 资源；`src/usv_fusion/bev/` 等体积较大，**不属于仿真最小构建集**，可按需排除。

## 文档与入口总览

| 路径 | 说明 |
|------|------|
| [src/usv_simulation/docs/docs_v3/QUICK_START.md](src/usv_simulation/docs/docs_v3/QUICK_START.md) | **用户向**：Docker / 本机环境、首次编译、**怎么跑 launch**、配置与话题 |
| [src/usv_simulation/docker/README.md](src/usv_simulation/docker/README.md) | **Docker**：Hub 镜像 `xyjy949/humble2harmonic`、Nav2 现状、**X11 + `--gpus all`** 推荐 `docker run`、容器内分步编译与验证 |
| [src/usv_simulation/README.md](src/usv_simulation/README.md) | 仿真平台说明、依赖与文档索引 |
| [src/usv_simulation/docs/docs_v3/仿真仓库结构说明.md](src/usv_simulation/docs/docs_v3/仿真仓库结构说明.md) | **架构向**：目录与包职责 |
| [src/usv_simulation/usv_sim_full/config/notes_config.md](src/usv_simulation/usv_sim_full/config/notes_config.md) | **配置索引**：各 YAML 由谁消费、与 launch / `session_manager` 如何衔接 |
| [src/usv_interfaces/README.md](src/usv_interfaces/README.md) | 统一消息与 topic 常量 |
| [CHANGELOG.md](CHANGELOG.md) | 版本与变更记录 |
| [LICENSE](LICENSE) / [NOTICE](NOTICE) | 许可证与第三方说明 |

建议阅读顺序：**本页支持矩阵** → **QUICK_START §0～§1**；若用容器 GUI，以 **docker/README.md** 中带 X11 与 GPU 的完整 `docker run` 为准（无 NVIDIA 或未装 Container Toolkit 时删掉 `--gpus all`）。

## 最小构建（仿真 + 接口）

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
- 全工作区粗暴安装依赖时也可用：`rosdep install --from-paths src --ignore-src -r -y`（可能解析到更多包，仿真主线仍以 `usv_interfaces` + `usv_simulation` 为推荐范围）。

仅接口包时：`./scripts/clean_build.sh --packages-select usv_interfaces`

## Docker 要点（摘要）

- **镜像**：团队基础环境 **`xyjy949/humble2harmonic`**（Humble + Harmonic）；Hub 上 **`:latest` 默认不含 Nav2**，Nav2 仿真需在容器内 `apt install ros-humble-navigation2` 或使用仓库内 **`Dockerfile.humble2harmonic_nav2`** 构建 `:nav2` 标签（详见 **docker/README.md**）。
- **推荐 `docker run`**：`--network host`、挂载仓库根到 **`/workspace`**、`-w /workspace`；带 Gazebo/RViz 时加 **X11** 与 **`--gpus all`**（细节与备用 `Xauthority` 示例见 **docker/README.md**）。
- **宿主 `docker run` 可在任意目录执行**；`-v` 使用仓库根的**绝对路径**即可。

## 发版与标签

- 版本号与变更见 [CHANGELOG.md](CHANGELOG.md)。
- 建议标签格式：`v0.1.0`（与 `CHANGELOG` 中 **Unreleased** 转正时一致）。

## 许可证

本项目默认以 [Apache License 2.0](LICENSE) 分发；VRX、marine_msgs、foxglove-sdk 等保留各自许可证，详见 [NOTICE](NOTICE) 与 [src/usv_simulation/third_party/README.md](src/usv_simulation/third_party/README.md)。
