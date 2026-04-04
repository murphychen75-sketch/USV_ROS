"""
毫米波最小仿真入口：复用 main.launch.py 的组装逻辑，默认配置为 mmwave_sydney_minimal.yaml。

- 世界：sydney_regatta（配置内 environment.world_name）
- 单船：spawn 对准 mb_marker_buoy_red；毫米波 + 同轴略高激光（对照点云）；无自定义障碍与动态场景；默认不启 RViz

用法：
  source install/setup.bash
  ros2 launch usv_sim_full mmwave_sydney_minimal.launch.py

可用参数与 main.launch.py 一致，例如 config_path:=/path/to/other.yaml
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    pkg_share = get_package_share_directory('usv_sim_full')
    default_minimal = os.path.join(pkg_share, 'config', 'mmwave_sydney_minimal.yaml')
    default_localization_params = os.path.join(pkg_share, 'config', 'robot_localization_gps.yaml')
    main_launch = os.path.join(pkg_share, 'launch', 'main.launch.py')

    return LaunchDescription([
        DeclareLaunchArgument(
            'config_path',
            default_value=default_minimal,
            description='毫米波最小验证用 YAML；结构与 full_config 相同',
        ),
        DeclareLaunchArgument(
            'enable_robot_localization',
            default_value='false',
            description='同 main.launch.py',
        ),
        DeclareLaunchArgument(
            'localization_params_file',
            default_value=default_localization_params,
            description='同 main.launch.py',
        ),
        DeclareLaunchArgument(
            'localization_start_delay',
            default_value='5.0',
            description='同 main.launch.py',
        ),
        DeclareLaunchArgument(
            'use_static_map_odom_tf',
            default_value='true',
            description='同 main.launch.py',
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(main_launch),
            launch_arguments={
                'config_path': LaunchConfiguration('config_path'),
                'enable_robot_localization': LaunchConfiguration('enable_robot_localization'),
                'localization_params_file': LaunchConfiguration('localization_params_file'),
                'localization_start_delay': LaunchConfiguration('localization_start_delay'),
                'use_static_map_odom_tf': LaunchConfiguration('use_static_map_odom_tf'),
            }.items(),
        ),
    ])
