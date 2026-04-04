# 1. 基础镜像：使用官方 ROS 2 Humble (基于 Ubuntu 22.04)
FROM osrf/ros:humble-desktop-full

# 设置非交互模式，防止安装过程中卡住
ENV DEBIAN_FRONTEND=noninteractive

# 2. 安装基础工具 (curl, wget, gnupg 等)
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    lsb-release \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# 3. 【关键步骤】添加 Gazebo 官方源
# Ubuntu 22.04 默认源里没有 Harmonic，必须加这个源才能找到
RUN curl https://packages.osrfoundation.org/gazebo.gpg --output /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] https://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null \
    && apt-get update

# 4. 【核心步骤】安装 Gazebo Harmonic 和 ROS 2 桥接包
RUN apt-get install -y \
    gz-harmonic \
    ros-humble-ros-gzharmonic \
    && rm -rf /var/lib/apt/lists/*

# 5. 设置环境变量
# 告诉系统默认使用 Harmonic 版本
ENV GZ_VERSION=harmonic

# 6. 配置入口
# 每次进入容器自动 source ROS 环境
RUN echo "source /opt/ros/humble/setup.bash" >> /root/.bashrc

CMD ["/bin/bash"]
