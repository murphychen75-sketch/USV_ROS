#!/bin/bash

# 自动确定工作空间路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="${SCRIPT_DIR}"

echo "工作空间根目录: ${WORKSPACE_ROOT}"

# 设置Gazebo模型路径以确保能够找到WAM-V模型
export GZ_SIM_RESOURCE_PATH=${GZ_SIM_RESOURCE_PATH}:${WORKSPACE_ROOT}/install/vrx_gz/share/vrx_gz/models
export GZ_SIM_RESOURCE_PATH=${GZ_SIM_RESOURCE_PATH}:${WORKSPACE_ROOT}/install/wamv_description/share
export GZ_SIM_RESOURCE_PATH=${GZ_SIM_RESOURCE_PATH}:${WORKSPACE_ROOT}/install/wamv_gazebo/share

# 设置经典Gazebo模型路径
export GAZEBO_MODEL_PATH=${GAZEBO_MODEL_PATH}:${WORKSPACE_ROOT}/install/wamv_description/share
export GAZEBO_MODEL_PATH=${GAZEBO_MODEL_PATH}:${WORKSPACE_ROOT}/install/wamv_gazebo/share

# 启动仿真
source ${WORKSPACE_ROOT}/install/setup.bash

# 在启动仿真前等待一段时间，确保所有资源已准备就绪
echo "等待资源加载..."
sleep 2

ros2 launch usv_sim_full main.launch.py config_path:="${WORKSPACE_ROOT}/install/usv_sim_full/share/usv_sim_full/config/full_config.yaml"