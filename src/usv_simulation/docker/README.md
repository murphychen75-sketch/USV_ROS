USV_Simulation Docker helper

## 推荐：复用 Docker Hub 镜像 `xyjy949/humble2harmonic`

团队维护的 **Humble + Harmonic（gz）** 基础环境已发布为 **`xyjy949/humble2harmonic`**，避免每人本地重复构建 Gazebo/OSRF 层。

### 默认目标 vs 当前 Hub 状态

- **默认目标（团队约定）**：仿真与 Nav2 全套流程应在 **已包含 Nav2** 的镜像中完成（免每次 `apt install`、环境一致）。该形态将通过 **重新构建并上传** Docker Hub 提供（例如专用标签或合并进 `:latest`）。
- **当前 Hub 上的 `:latest`**：**尚未内置 Nav2**，仅含 Humble + Harmonic（gz）等基础层。需要跑 `nav2_sim_full_bringup.launch.py` / `nav2_thruster_bringup.launch.py` 时，请先在容器内安装 **`ros-humble-navigation2`**（含 `nav2_bringup`、`nav2_mppi_controller` 等，与 [`radar_nav2_param.yaml`](../usv_sim_full/config/radar_nav2_param.yaml) 中 MPPI 配置一致）。

**现阶段推荐**：拉取当前 **不含 Nav2** 的基础镜像，进入容器后 **用 apt 安装 Nav2**（及 colcon/rosdep），见下方 **方式 A**。待 Hub 更新为带 Nav2 的镜像后，可直接 `docker pull` 对应标签，省略容器内安装步骤。

### 方式 A：基础镜像 + 容器内安装 Nav2（现阶段默认）

**在哪个目录执行？**

- **宿主机**：`docker pull` / `docker run` **可在任意当前目录执行**，不依赖 `cd` 到仓库里；关键是把 `-v` 里的 **`/path/to/USV_ROS` 换成你本机仓库根的绝对路径**（含 `src/`、`scripts/` 的那一层）。
- **容器内**：`-w /workspace` 会把 shell 的起始目录设为挂载点，即 **仓库根**（与宿主机 `USV_ROS` 对应）。下面 `rosdep`、`./scripts/clean_build.sh`、`ros2 launch` 均假设 **当前目录已是 `/workspace`（仓库根）**；若曾 `cd` 到子目录，请先 `cd /workspace`。

#### 宿主 Linux：X11 真显示（Gazebo / RViz）

在 **Linux 宿主机 + X11**（多数桌面为 XWayland 时通常仍可用）下，要让容器内 **Gazebo、RViz** 画到宿主屏幕，需要把 **显示环境变量** 和 **X11 socket** 挂进容器。

**是否必须「重启 Docker」？**

- **不必**执行 `systemctl restart docker` 或重启 Docker Desktop。
- **必须**用带 X11 参数的 **`docker run` 新建一个容器**：已在跑的容器 **不能**事后补上 `-e DISPLAY`、`-v /tmp/.X11-unix`（挂载与部分环境在创建时固定）。做法是：在容器里 `exit`（若需保留工作区状态，依赖已挂载的 `/workspace` 目录即可），再在宿主用下面完整命令重新 `docker run`。

**宿主机先放行本机连接 X（每次登录或开机后执行一次即可）：**

```bash
xhost +local:
# 更窄：仅 root 用户（部分环境） xhost +SI:localuser:root
```

**与方式 A 配套的 `docker run`（含 X11 + GPU；不需要 GUI 时可删掉三行 `-e DISPLAY` / `QT_X11…` / `-v /tmp/.X11-unix`；无 NVIDIA 或未装 [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) 时删掉 `--gpus all`）：**

```bash
docker pull xyjy949/humble2harmonic:latest
xhost +local:
docker run -it --rm \
  --network host \
  --gpus all \
  -e DISPLAY=${DISPLAY} \
  -e QT_X11_NO_MITSHM=1 \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -v /path/to/USV_ROS:/workspace \
  -w /workspace \
  xyjy949/humble2harmonic:latest \
  bash -lc 'apt-get update && apt-get install -y ros-humble-navigation2 python3-colcon-common-extensions python3-rosdep && exec bash'
```

**仍报 `could not connect to display` 时**，可再挂载 Xauthority（宿主 `echo $DISPLAY` 应为 `:0` 等）：

```bash
docker run -it --rm \
  --network host \
  --gpus all \
  -e DISPLAY=${DISPLAY} \
  -e QT_X11_NO_MITSHM=1 \
  -e XAUTHORITY=/tmp/.docker.xauth \
  -v $HOME/.Xauthority:/tmp/.docker.xauth:ro \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -v /path/to/USV_ROS:/workspace \
  -w /workspace \
  xyjy949/humble2harmonic:latest \
  bash
```

**NVIDIA**：推荐命令已含 `--gpus all`。若需完整 OpenGL/Vulkan 能力，可再追加 `-e NVIDIA_DRIVER_CAPABILITIES=all`（按需）。

**安全提示**：`xhost +local:` 仅建议在受信任的开发机使用；不用 GUI 时可 `xhost -local:`。

```bash
# 无头 / CI：不需要 Gazebo 窗口时可省略 X11 三行，仅保留挂载与 network，例如：
docker run -it --rm \
  --network host \
  -v /path/to/USV_ROS:/workspace \
  -w /workspace \
  xyjy949/humble2harmonic:latest \
  bash -lc 'apt-get update && apt-get install -y ros-humble-navigation2 python3-colcon-common-extensions python3-rosdep && exec bash'
```

进入容器后，在 **`/workspace`（仓库根）** 按下面模块顺序执行；**首次配置**走模块 1～6，**日常只跑仿真**通常只需模块 1 + 6（及按需 7）。

#### 1. 加载 ROS 2 Humble

| 目的 | 将当前 shell 接入 Humble：`ros2`、`colcon`、基础消息包路径可用。 |
|------|------------------------------------------------------------------|

```bash
source /opt/ros/humble/setup.bash
```

#### 2. 刷新 apt 索引（rosdep / apt 安装前）

| 目的 | 保证 `rosdep` 解析到的 deb 包名与仓库一致；长时间未更新的容器建议先执行。 |
|------|---------------------------------------------------------------------------|

```bash
apt-get update
```

#### 3. 用 rosdep 安装接口与仿真包的系统依赖

| 目的 | 根据 `package.xml` 安装编译/运行所需的系统包（非 ROS 包本身）；范围为本仓库的 `usv_interfaces` 与 `usv_simulation`。 |
|------|------------------------------------------------------------------------------------------------------------------|

```bash
rosdep install --from-paths src/usv_interfaces src/usv_simulation --ignore-src -r -y
```

#### 4.（按需）清理宿主编译残留

| 目的 | 若工作区曾在**宿主机**上 `colcon build` 过，`build/` 里可能缓存了宿主机绝对路径，在容器内 CMake 会报错。仅在出现路径相关错误、或首次在容器内编译时执行。 |
|------|--------------------------------------------------------------------------------------------------------------------------------------------------------|

```bash
rm -rf build install log
```

#### 5. 编译工作区（至 `usv_sim_full`）

| 目的 | 生成 `install/`，使自定义消息、`usv_sim_full` 等包可被 `ros2 launch` 找到；与仓库根 [`scripts/clean_build.sh`](../../../scripts/clean_build.sh) 行为一致。`colcon --packages-up-to` **只编目标包及其在 `package.xml` 中声明的依赖**；`usv_sim_full` 已用 `exec_depend` 拉上 **`gy_radar_driver`、`radar_gz_bridge`** 等，故本命令会一并编译，避免 `package 'gy_radar_driver' not found`。 |
|------|--------------------------------------------------------------------------------------------------------------------------------------------------------|

```bash
./scripts/clean_build.sh --packages-up-to usv_sim_full
```

#### 6. 加载工作区 overlay

| 目的 | 叠加本仓库编译结果到 ROS 环境；之后才能 `ros2 launch usv_sim_full ...`。 |
|------|--------------------------------------------------------------------------|

```bash
source install/setup.bash
```

#### 7. 启动仿真（示例：Nav2 全套）

| 目的 | 拉起 Gazebo / 船模 / 导航等 launch；其他入口见 [`docs/docs_v3/QUICK_START.md`](../docs/docs_v3/QUICK_START.md) §2。 |
|------|---------------------------------------------------------------------------------------------------------------------|

```bash
ros2 launch usv_sim_full nav2_sim_full_bringup.launch.py
```

**一次性复制（首次从零到可 launch）**：

```bash
source /opt/ros/humble/setup.bash
apt-get update
rosdep install --from-paths src/usv_interfaces src/usv_simulation --ignore-src -r -y
rm -rf build install log
colcon build
source install/setup.bash
ros2 launch usv_sim_full nav2_sim_full_bringup.launch.py
```

**同一容器、新开终端时**：一般只需 **模块 1** + **模块 6**（若未改代码、未删 `install/`）；Nav2 已在首次 `docker run ... bash -lc 'apt-get install ...'` 中装过则**不必**再 `apt-get install`。源码或依赖有变时重做 **模块 3～5**。

### 方式 B：本地构建「含 Nav2」子镜像（与后续 Hub 上传对齐）

在本目录提供了 **`Dockerfile.humble2harmonic_nav2`**（`FROM xyjy949/humble2harmonic`，预装 Nav2、colcon、rosdep 及仿真常用 gz 开发包等）。可在本地先与 **方式 A** 行为一致地固化环境，再 **推送 Docker Hub** 供团队直接 `pull`（与上文「默认目标」对应）。

```bash
cd /path/to/USV_ROS
docker build -f src/usv_simulation/docker/Dockerfile.humble2harmonic_nav2 -t xyjy949/humble2harmonic:nav2 .
docker push xyjy949/humble2harmonic:nav2
# 可选：发布稳定后将 :latest 指向含 Nav2 的 digest，或在文档中固定推荐标签（如 :nav2）
```

GUI（RViz / Gazebo）的 X11 / `--gpus all` 与 **方式 A** 中 **「宿主 Linux：X11 真显示」** 一致；用本镜像 `docker run` 时同样加上 `DISPLAY`、`/tmp/.X11-unix` 等。

---

## 从源码构建：本目录 `Dockerfile`

本目录的 `Dockerfile` 用于在 **Ubuntu 22.04 + ROS 2 Humble + Gazebo Harmonic（gz-harmonic）** 上从零搭容器环境，与仓库根 [README.md](../../README.md) 中的**支持矩阵**一致（仿真主线以 Harmonic 为准，旧文档中的 “Garden” 表述可忽略）。

Important notes and assumptions
- Base OS: Ubuntu 22.04 (jammy).
- ROS distribution: Humble（镜像 `osrf/ros:humble-desktop-full`）。
- Gazebo：通过 OSRF 源安装 **gz-harmonic** 与 **ros-humble-ros-gzharmonic**；若 apt 报错，请核对 [Gazebo 安装文档](https://gazebosim.org/docs/harmonic/install_ubuntu/) 与当时软件源是否可用。
- **构建策略**：请在容器内于工作区根目录执行与主机相同的 colcon 流程，例如  
  `source /opt/ros/humble/setup.bash && rosdep install --from-paths src/usv_interfaces src/usv_simulation --ignore-src -r -y`  
  再  
  `./scripts/clean_build.sh --packages-up-to usv_sim_full`。  
  不要依赖「大量 `|| true` 静默跳过 apt」作为发布镜像的基础；若需一键镜像，应在 Dockerfile 中**显式列出**仿真链路的 deb 依赖并让安装失败时构建失败。

## Build

从工作区根目录指定 Dockerfile 路径构建（示例）：

```bash
cd /path/to/USV_ROS
docker build -f src/usv_simulation/docker/Dockerfile -t usv_sim:humble-harmonic .
```

Run (GUI / RViz / Gazebo)

与 **方式 A** 顶部 **「宿主 Linux：X11 真显示」** 相同思路：宿主 `xhost +local:`，容器传入 `DISPLAY`、`QT_X11_NO_MITSHM=1`、挂载 `/tmp/.X11-unix:rw`；**无需重启 dockerd，需重新 `docker run` 建容器**。Hub 镜像 `xyjy949/humble2harmonic` 见该节完整示例。

本仓库构建的 `usv_sim:humble-harmonic` 示例：

```bash
xhost +local:
docker run -it --rm \
  --network host \
  --gpus all \
  -e DISPLAY=${DISPLAY} \
  -e QT_X11_NO_MITSHM=1 \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  --privileged \
  usv_sim:humble-harmonic
```

若遇 MIT-SHM / 共享内存问题，可保留 `QT_X11_NO_MITSHM=1`。无 NVIDIA 或未装 [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) 时删掉 `--gpus all`。

Usage inside container
- The entrypoint sources ROS 2 and workspace overlay (if built). Then you'll be in a shell.
- To build again inside container:
    colcon build --merge-install
- To run the quick start script (if you prefer):
    /bin/bash -lc ". install/setup.bash; bash src/usv_sim_full/sh/quick_start.sh"

Troubleshooting
- If apt cannot find ros-gz packages, check OSRF packaging for **Humble + Harmonic** and ensure `gazebo-stable.list` is present (see Dockerfile in this folder).
- For GUI apps on Wayland or remote desktops, you might need extra configuration (XWayland, pipewire, or VNC). See your distro/desktop docs.

**可选后续增强**（未默认实现）：非 root 用户、多阶段构建缓存、`docker-compose` 与 X11/GPU 映射等，按部署需求自行扩展。