"""
在已运行的完整仿真（如 ros2 launch usv_sim_full main.launch.py）中，额外 spawn 毫米波验证体。

不修改主 USV；在独立话题上出点云，用于判断「插件 + 当前 gz 环境」是否正常。
默认世界 sydney_regatta、话题 /mmwave_spawn_test/points（与 usv_1/.../mmwave 分离）。

用法：
  source install/setup.bash
  ros2 launch usv_sim_full spawn_mmwave_probe_in_running_sim.launch.py

验证：
  ros2 topic echo /mmwave_spawn_test/points --qos-reliability best_effort

若有点云而集成话题仍无：问题在 URDF/插件参数/命名空间侧；若仍无：检查 GZ_SIM_SYSTEM_PLUGIN_PATH 是否在「启动 gz 的进程」中生效。
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    spawn_launch = os.path.join(
        get_package_share_directory("usv_mmwave_sim"),
        "launch",
        "spawn_ego_mmwave_validation.launch.py",
    )
    return LaunchDescription([
        DeclareLaunchArgument(
            "world",
            default_value="sydney_regatta",
            description="须与当前 Gazebo 世界名一致",
        ),
        DeclareLaunchArgument(
            "topic",
            default_value="/mmwave_spawn_test/points",
        ),
        DeclareLaunchArgument(
            "spawn_name",
            default_value="mmwave_spawn_test",
        ),
        DeclareLaunchArgument(
            "x", default_value="15.0",
        ),
        DeclareLaunchArgument(
            "y", default_value="15.0",
        ),
        DeclareLaunchArgument(
            "z", default_value="3.0",
        ),
        DeclareLaunchArgument(
            "delay_s", default_value="3.0",
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(spawn_launch),
            launch_arguments={
                "world": LaunchConfiguration("world"),
                "topic": LaunchConfiguration("topic"),
                "spawn_name": LaunchConfiguration("spawn_name"),
                "x": LaunchConfiguration("x"),
                "y": LaunchConfiguration("y"),
                "z": LaunchConfiguration("z"),
                "delay_s": LaunchConfiguration("delay_s"),
            }.items(),
        ),
    ])
